from __future__ import annotations

from datetime import datetime, timezone
import json

from fastapi import HTTPException, status
from sqlalchemy import String, asc, cast, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.enums import ProductKind
from app.models import (
    DeliveryAddressNode,
    DeliveryLocationCache,
    DeliveryZonePricing,
    Order,
    Product,
    ProductCategory,
    ProductConsumptionComponent,
    ProductSecondaryLink,
    RestaurantTable,
)
from app.schemas import TableSessionSettlementOut
from app.tracking import decode_public_order_tracking_code
from app.orchestration.service_bridge import (
    app_archive_product,
    app_create_product,
    app_create_product_category,
    app_create_table,
    app_delete_product_category,
    app_delete_product_permanently,
    app_delete_table,
    app_get_delivery_fee_setting,
    app_get_delivery_location_provider_settings,
    app_get_delivery_policy_settings,
    app_get_operational_capabilities,
    app_get_system_context_settings,
    app_get_table_session_snapshot,
    app_list_active_table_sessions,
    app_list_product_categories,
    app_list_tables_with_session_summary,
    app_settle_table_session,
    app_update_delivery_fee_setting,
    app_update_delivery_location_provider_settings,
    app_update_delivery_policy_settings,
    app_update_product,
    app_update_product_category,
    app_update_table,
    app_upload_product_image,
)
from application.operations_engine.domain.workflow_profiles import resolve_public_workflow_profile
from infrastructure.providers import DeliveryLocationNode, get_delivery_location_provider


class OperationsRepository:
    DELIVERY_ADDRESS_LEVELS = (
        "admin_area_level_1",
        "admin_area_level_2",
        "locality",
        "sublocality",
    )

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _normalize_product_kind_filter(kind: str) -> str:
        normalized = (kind or "all").strip().lower()
        if normalized in {"sellable", "primary"}:
            return ProductKind.PRIMARY.value
        if normalized in {"internal", "secondary"}:
            return ProductKind.SECONDARY.value
        return "all"

    @staticmethod
    def _product_load_options():
        return (
            selectinload(Product.secondary_links).selectinload(ProductSecondaryLink.secondary_product),
            selectinload(Product.consumption_components).selectinload(ProductConsumptionComponent.warehouse_item),
        )

    @staticmethod
    def _public_products_stmt():
        return (
            select(Product)
            .options(
                selectinload(Product.secondary_links).selectinload(ProductSecondaryLink.secondary_product),
            )
            .where(
                Product.available.is_(True),
                Product.is_archived.is_(False),
                Product.kind == ProductKind.PRIMARY.value,
            )
        )

    @classmethod
    def _normalize_delivery_address_level(cls, level: str) -> str:
        normalized = (level or "").strip().lower()
        if normalized not in cls.DELIVERY_ADDRESS_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="مستوى العنوان غير مدعوم ضمن الشجرة اليدوية الحالية.",
            )
        return normalized

    def create_table(self, *, status_value: str) -> RestaurantTable:
        return app_create_table(self._db, status_value=status_value)

    def update_table(self, *, table_id: int, status_value: str) -> RestaurantTable:
        return app_update_table(self._db, table_id=table_id, status_value=status_value)

    def delete_table(self, *, table_id: int) -> None:
        app_delete_table(self._db, table_id=table_id)

    def settle_table_session(
        self,
        *,
        table_id: int,
        performed_by: int,
        amount_received: float | None = None,
    ) -> TableSessionSettlementOut:
        return app_settle_table_session(
            self._db,
            table_id=table_id,
            performed_by=performed_by,
            amount_received=amount_received,
        )

    def list_tables_with_session_summary(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        table_ids: list[int] | None = None,
    ) -> list[dict[str, object]]:
        return app_list_tables_with_session_summary(
            self._db,
            offset=offset,
            limit=limit,
            table_ids=table_ids,
        )

    def list_active_table_sessions(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[dict[str, object]]:
        return app_list_active_table_sessions(self._db, offset=offset, limit=limit)

    def get_table_session_snapshot(self, *, table_id: int) -> dict[str, object]:
        return app_get_table_session_snapshot(self._db, table_id=table_id)

    def list_products(
        self,
        *,
        kind: str,
        offset: int,
        limit: int,
    ) -> list[Product]:
        normalized_kind = self._normalize_product_kind_filter(kind)
        stmt = select(Product).options(*self._product_load_options())
        if normalized_kind == ProductKind.PRIMARY.value:
            stmt = stmt.where(Product.kind == ProductKind.PRIMARY.value)
        elif normalized_kind == ProductKind.SECONDARY.value:
            stmt = stmt.where(Product.kind == ProductKind.SECONDARY.value)
        return (
            self._db.execute(
                stmt.order_by(Product.id.asc())
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )

    def list_products_paged(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_direction: str,
        archive_state: str,
        kind: str,
    ) -> tuple[list[Product], int]:
        conditions = []
        if archive_state == "active":
            conditions.append(Product.is_archived.is_(False))
        elif archive_state == "archived":
            conditions.append(Product.is_archived.is_(True))
        normalized_kind = self._normalize_product_kind_filter(kind)
        if normalized_kind == ProductKind.PRIMARY.value:
            conditions.append(Product.kind == ProductKind.PRIMARY.value)
        elif normalized_kind == ProductKind.SECONDARY.value:
            conditions.append(Product.kind == ProductKind.SECONDARY.value)

        normalized_search = (search or "").strip()
        if normalized_search:
            like_value = f"%{normalized_search}%"
            conditions.append(
                or_(
                    cast(Product.id, String).ilike(like_value),
                    Product.name.ilike(like_value),
                    Product.category.ilike(like_value),
                    Product.description.ilike(like_value),
                )
            )

        total_stmt = select(func.count(Product.id))
        if conditions:
            total_stmt = total_stmt.where(*conditions)
        total = int(self._db.execute(total_stmt).scalar_one() or 0)

        sort_map = {
            "id": Product.id,
            "name": Product.name,
            "category": Product.category,
            "price": Product.price,
            "available": Product.available,
        }
        direction = asc if sort_direction == "asc" else desc
        sort_column = sort_map.get(sort_by, Product.id)

        stmt = select(Product).options(*self._product_load_options())
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(direction(sort_column), desc(Product.id))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = self._db.execute(stmt).unique().scalars().all()
        return items, total

    def list_product_categories(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[dict[str, object]]:
        return app_list_product_categories(self._db, offset=offset, limit=limit)

    def create_product_category(
        self,
        *,
        name: str,
        active: bool,
        sort_order: int,
    ) -> ProductCategory:
        return app_create_product_category(
            self._db,
            name=name,
            active=active,
            sort_order=sort_order,
        )

    def update_product_category(
        self,
        *,
        category_id: int | None,
        name: str,
        active: bool,
        sort_order: int,
    ) -> ProductCategory:
        return app_update_product_category(
            self._db,
            category_id=category_id,
            name=name,
            active=active,
            sort_order=sort_order,
        )

    def delete_product_category(self, *, category_id: int) -> None:
        app_delete_product_category(self._db, category_id=category_id)

    def create_product(
        self,
        *,
        name: str,
        description: str | None,
        price: float,
        kind: ProductKind,
        available: bool,
        category_id: int | None,
        secondary_links,
        consumption_components,
    ) -> Product:
        return app_create_product(
            self._db,
            name=name,
            description=description,
            price=price,
            kind=kind,
            available=available,
            category_id=category_id,
            secondary_links=secondary_links,
            consumption_components=consumption_components,
        )

    def update_product(
        self,
        *,
        product_id: int,
        name: str,
        description: str | None,
        price: float,
        kind: ProductKind,
        available: bool,
        category_id: int | None,
        secondary_links,
        consumption_components,
        is_archived: bool | None,
    ) -> Product:
        return app_update_product(
            self._db,
            product_id=product_id,
            name=name,
            description=description,
            price=price,
            kind=kind,
            available=available,
            category_id=category_id,
            secondary_links=secondary_links,
            consumption_components=consumption_components,
            is_archived=is_archived,
        )

    def upload_product_image(
        self,
        *,
        product_id: int,
        data_base64: str,
        mime_type: str,
    ) -> Product:
        return app_upload_product_image(
            self._db,
            product_id=product_id,
            data_base64=data_base64,
            mime_type=mime_type,
        )

    def archive_product(self, *, product_id: int) -> None:
        app_archive_product(self._db, product_id=product_id)

    def delete_product_permanently(self, *, product_id: int) -> None:
        app_delete_product_permanently(self._db, product_id=product_id)

    def list_public_products(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[Product]:
        return (
            self._db.execute(
                self._public_products_stmt()
                .order_by(Product.id.asc())
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )

    def get_public_order_journey_bootstrap(self, *, table_id: int | None = None) -> dict[str, object]:
        products = (
            self._db.execute(self._public_products_stmt().order_by(Product.category.asc(), Product.id.asc()))
            .unique()
            .scalars()
            .all()
        )
        secondary_products = (
            self._db.execute(
                select(Product)
                .where(
                    Product.available.is_(True),
                    Product.is_archived.is_(False),
                    Product.kind == ProductKind.SECONDARY.value,
                )
                .order_by(Product.category.asc(), Product.id.asc())
            )
            .scalars()
            .all()
        )
        categories: dict[str, list[dict[str, object]]] = {}
        for product in products:
            categories.setdefault(product.category, []).append(
                {
                    "id": int(product.id),
                    "name": product.name,
                    "description": product.description,
                    "price": float(product.price),
                    "category": product.category,
                    "image_path": product.image_path,
                    "secondary_options": [],
                }
            )

        catalog_categories = [
            {
                "name": category_name,
                "products": category_products,
            }
            for category_name, category_products in sorted(categories.items(), key=lambda item: item[0].lower())
        ]

        secondary_catalog = [
            {
                "product_id": int(product.id),
                "name": product.name,
                "description": product.description,
                "price": float(product.price),
                "image_path": product.image_path,
                "sort_order": 0,
                "is_default": False,
                "max_quantity": 99,
            }
            for product in secondary_products
        ]

        capabilities = self.get_operational_capabilities()
        delivery_policies = self.get_delivery_policies()
        table_context = {
            "table_id": table_id,
            "has_table_context": table_id is not None,
            "has_active_session": False,
            "table_status": None,
            "total_orders": 0,
            "active_orders_count": 0,
            "unsettled_orders_count": 0,
            "unpaid_total": 0.0,
            "latest_order_status": None,
        }
        if table_id is not None:
            snapshot = self.get_public_table_session(table_id=table_id)
            table = snapshot.get("table")
            table_row_id = int(getattr(table, "id", 0) or 0)
            table_row_status = getattr(table, "status", None)
            table_context = {
                "table_id": table_row_id or table_id,
                "has_table_context": True,
                "has_active_session": bool(snapshot.get("has_active_session", False)),
                "table_status": table_row_status,
                "total_orders": int(snapshot.get("total_orders", 0) or 0),
                "active_orders_count": int(snapshot.get("active_orders_count", 0) or 0),
                "unsettled_orders_count": int(snapshot.get("unsettled_orders_count", 0) or 0),
                "unpaid_total": float(snapshot.get("unpaid_total", 0.0) or 0.0),
                "latest_order_status": snapshot.get("latest_order_status"),
            }

        allowed_order_types = ["takeaway", "dine-in"]
        if capabilities.get("delivery_feature_enabled", False):
            allowed_order_types.insert(1, "delivery")

        delivery_settings = self.get_delivery_settings()
        workflow_profile = resolve_public_workflow_profile(
            activation_stage_id=str(capabilities.get("activation_stage_id") or "base"),
            kitchen_feature_enabled=bool(capabilities.get("kitchen_feature_enabled", True)),
        )

        return {
            "meta": {
                "journey_version": "v1",
                "generated_at": datetime.now(timezone.utc),
            },
            "catalog": {
                "categories": catalog_categories,
                "secondary_products": secondary_catalog,
            },
            "capabilities": capabilities,
            "delivery": {
                "delivery_fee": float(delivery_settings["delivery_fee"]),
                "min_order_amount": float(delivery_policies["min_order_amount"]),
                "pricing_mode": str(delivery_settings["pricing_mode"]),
                "structured_locations_enabled": bool(delivery_settings["structured_locations_enabled"]),
                "zones_configured": bool(delivery_settings["active_zones_count"] > 0),
            },
            "table_context": table_context,
            "journey_rules": {
                "allowed_order_types": allowed_order_types,
                "default_order_type": "dine-in" if table_id is not None else "takeaway",
                "workflow_profile": workflow_profile,
                "require_phone_for_takeaway": False,
                "require_phone_for_delivery": True,
                "require_address_for_delivery": True,
                "allow_manual_table_selection": table_id is None,
            },
        }

    def get_public_order_tracking(self, *, tracking_code: str) -> Order | None:
        order_id = decode_public_order_tracking_code(tracking_code)
        if order_id is None:
            return None
        return (
            self._db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.id == order_id)
            )
            .scalars()
            .first()
        )

    def list_public_tables(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[RestaurantTable]:
        return (
            self._db.execute(
                select(RestaurantTable)
                .order_by(RestaurantTable.id.asc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def get_public_table_session(self, *, table_id: int) -> dict[str, object]:
        return app_get_table_session_snapshot(self._db, table_id=table_id)

    def get_delivery_settings(self) -> dict[str, object]:
        active_zones_count = self._count_active_delivery_zones()
        return {
            "delivery_fee": app_get_delivery_fee_setting(self._db),
            "pricing_mode": "manual_tree" if active_zones_count > 0 else "fixed",
            "structured_locations_enabled": active_zones_count > 0,
            "active_zones_count": active_zones_count,
            "system_context": app_get_system_context_settings(self._db),
        }

    def get_delivery_location_provider_settings(self) -> dict[str, object]:
        return app_get_delivery_location_provider_settings(self._db)

    def update_delivery_location_provider_settings(
        self,
        *,
        provider: str,
        enabled: bool,
        geonames_username: str | None,
        country_codes: list[str],
        cache_ttl_hours: int,
        actor_id: int,
    ) -> dict[str, object]:
        return app_update_delivery_location_provider_settings(
            self._db,
            provider=provider,
            enabled=enabled,
            geonames_username=geonames_username,
            country_codes=country_codes,
            cache_ttl_hours=cache_ttl_hours,
            actor_id=actor_id,
        )

    def list_delivery_address_nodes(
        self,
        *,
        parent_id: int | None = None,
        public_only: bool = False,
    ) -> dict[str, object]:
        stmt = select(DeliveryAddressNode).where(DeliveryAddressNode.parent_id == parent_id)
        if public_only:
            stmt = stmt.where(
                DeliveryAddressNode.active.is_(True),
                DeliveryAddressNode.visible_in_public.is_(True),
            )
        stmt = stmt.order_by(
            DeliveryAddressNode.sort_order.asc(),
            DeliveryAddressNode.display_name.asc(),
            DeliveryAddressNode.id.asc(),
        )
        items = self._db.execute(stmt).scalars().all()
        child_counts = self._load_delivery_address_child_counts([node.id for node in items])
        return {
            "parent_id": parent_id,
            "items": [self._delivery_address_to_payload(node, child_counts.get(int(node.id), 0)) for node in items],
            "total": len(items),
        }

    def create_delivery_address_node(
        self,
        *,
        parent_id: int | None,
        level: str,
        code: str,
        name: str,
        display_name: str,
        postal_code: str | None,
        notes: str | None,
        active: bool,
        visible_in_public: bool,
        sort_order: int,
        actor_id: int,
    ) -> DeliveryAddressNode:
        system_context = app_get_system_context_settings(self._db)
        normalized_level = self._normalize_delivery_address_level(level)
        parent = self._get_delivery_address_parent_or_validate(parent_id=parent_id, expected_level=normalized_level)
        normalized_code = code.strip()

        existing = self._db.execute(
            select(DeliveryAddressNode).where(
                DeliveryAddressNode.parent_id == parent_id,
                DeliveryAddressNode.code == normalized_code,
            )
        ).scalars().first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يوجد عنوان فرعي بنفس الرمز داخل هذا المستوى.",
            )

        now = datetime.now(timezone.utc)
        node = DeliveryAddressNode(
            parent_id=parent_id,
            level=normalized_level,
            country_code=str(system_context["country_code"]),
            code=normalized_code,
            name=name.strip(),
            display_name=display_name.strip(),
            postal_code=(postal_code or "").strip() or None,
            notes=(notes or "").strip() or None,
            active=bool(active),
            visible_in_public=bool(visible_in_public),
            sort_order=int(sort_order),
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
        )
        self._db.add(node)
        self._db.flush()
        return node

    def update_delivery_address_node(
        self,
        *,
        node_id: int,
        code: str,
        name: str,
        display_name: str,
        postal_code: str | None,
        notes: str | None,
        active: bool,
        visible_in_public: bool,
        sort_order: int,
        actor_id: int,
    ) -> DeliveryAddressNode:
        node = self._get_delivery_address_node_or_404(node_id=node_id)
        normalized_code = code.strip()
        duplicate = self._db.execute(
            select(DeliveryAddressNode).where(
                DeliveryAddressNode.parent_id == node.parent_id,
                DeliveryAddressNode.code == normalized_code,
                DeliveryAddressNode.id != node.id,
            )
        ).scalars().first()
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يوجد عنوان فرعي آخر بنفس الرمز داخل هذا المستوى.",
            )
        node.code = normalized_code
        node.name = name.strip()
        node.display_name = display_name.strip()
        node.postal_code = (postal_code or "").strip() or None
        node.notes = (notes or "").strip() or None
        node.active = bool(active)
        node.visible_in_public = bool(visible_in_public)
        node.sort_order = int(sort_order)
        node.updated_at = datetime.now(timezone.utc)
        node.updated_by = actor_id
        self._db.flush()
        return node

    def delete_delivery_address_node(self, *, node_id: int) -> None:
        root = self._get_delivery_address_node_or_404(node_id=node_id)
        subtree_ids = self._collect_delivery_address_subtree_ids(root_id=int(root.id))

        if subtree_ids:
            self._db.query(DeliveryZonePricing).filter(
                DeliveryZonePricing.location_key.in_([str(node_id_value) for node_id_value in subtree_ids])
            ).delete(synchronize_session=False)

        nodes_by_id = self._load_delivery_address_nodes_by_id(subtree_ids)
        for existing_id in reversed(subtree_ids):
            node = nodes_by_id.get(existing_id)
            if node is not None:
                self._db.delete(node)
        self._db.flush()

    def list_delivery_location_countries(self) -> dict[str, object]:
        settings = self.get_delivery_location_provider_settings()
        self._ensure_delivery_location_provider_ready(settings)
        provider_name = str(settings["provider"])
        cached_rows = self._get_cached_location_rows(provider=provider_name, parent_key=None)
        if cached_rows:
            return {
                "provider": provider_name,
                "parent_key": None,
                "items": [self._cache_row_to_payload(row) for row in cached_rows],
            }

        provider = get_delivery_location_provider(provider_name)
        items = provider.list_countries(
            username=str(settings["geonames_username"]),
            country_codes=list(settings["country_codes"]),
        )
        self._replace_cached_children(provider=provider_name, parent_key=None, nodes=items, ttl_hours=int(settings["cache_ttl_hours"]))
        return {
            "provider": provider_name,
            "parent_key": None,
            "items": [self._node_to_payload(node) for node in items],
        }

    def list_delivery_location_children(self, *, parent_key: str) -> dict[str, object]:
        settings = self.get_delivery_location_provider_settings()
        self._ensure_delivery_location_provider_ready(settings)
        provider_name = str(settings["provider"])
        cached_parent = self._get_cached_location_node(provider=provider_name, node_key=parent_key)
        if cached_parent is None and parent_key.startswith("geonames:country:"):
            self.list_delivery_location_countries()
            cached_parent = self._get_cached_location_node(provider=provider_name, node_key=parent_key)
        if cached_parent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعذر العثور على عقدة الموقع المطلوبة.")

        cached_children = self._get_cached_location_rows(provider=provider_name, parent_key=parent_key)
        if cached_children:
            return {
                "provider": provider_name,
                "parent_key": parent_key,
                "items": [self._cache_row_to_payload(row) for row in cached_children],
            }

        if not cached_parent.external_id:
            return {"provider": provider_name, "parent_key": parent_key, "items": []}

        provider = get_delivery_location_provider(provider_name)
        items = provider.list_children(
            username=str(settings["geonames_username"]),
            parent_external_id=str(cached_parent.external_id),
            parent_key=parent_key,
            parent_level=str(cached_parent.level),
            country_code=cached_parent.country_code,
        )
        self._replace_cached_children(provider=provider_name, parent_key=parent_key, nodes=items, ttl_hours=int(settings["cache_ttl_hours"]))
        return {
            "provider": provider_name,
            "parent_key": parent_key,
            "items": [self._node_to_payload(node) for node in items],
        }

    def get_delivery_policies(self) -> dict[str, object]:
        return app_get_delivery_policy_settings(self._db)

    def update_delivery_settings(self, *, delivery_fee: float, actor_id: int) -> dict[str, object]:
        value = app_update_delivery_fee_setting(self._db, delivery_fee=delivery_fee, actor_id=actor_id)
        active_zones_count = self._count_active_delivery_zones()
        return {
            "delivery_fee": value,
            "pricing_mode": "manual_tree" if active_zones_count > 0 else "fixed",
            "structured_locations_enabled": active_zones_count > 0,
            "active_zones_count": active_zones_count,
            "system_context": app_get_system_context_settings(self._db),
        }

    def list_delivery_zone_pricing(
        self,
        *,
        search: str | None = None,
        active_only: bool | None = None,
    ) -> dict[str, object]:
        stmt = select(DeliveryZonePricing).where(DeliveryZonePricing.provider == "manual")
        normalized_search = (search or "").strip()
        if normalized_search:
            like_value = f"%{normalized_search}%"
            stmt = stmt.where(
                or_(
                    DeliveryZonePricing.name.ilike(like_value),
                    DeliveryZonePricing.display_name.ilike(like_value),
                    DeliveryZonePricing.location_key.ilike(like_value),
                    DeliveryZonePricing.country_code.ilike(like_value),
                )
            )
        if active_only is not None:
            stmt = stmt.where(DeliveryZonePricing.active.is_(active_only))
        stmt = stmt.order_by(
            DeliveryZonePricing.sort_order.asc(),
            DeliveryZonePricing.display_name.asc(),
            DeliveryZonePricing.id.asc(),
        )
        items = self._db.execute(stmt).scalars().all()
        node_ids = [int(zone.location_key) for zone in items if str(zone.location_key).isdigit()]
        nodes_by_id = self._load_delivery_address_nodes_by_id(node_ids)
        payloads = []
        for zone in items:
            node = nodes_by_id.get(int(zone.location_key)) if str(zone.location_key).isdigit() else None
            payloads.append(self._delivery_zone_to_payload(zone, node))
        return {"items": payloads, "total": len(payloads)}

    def upsert_delivery_zone_pricing(
        self,
        *,
        node_id: int,
        delivery_fee: float,
        active: bool,
        sort_order: int,
        actor_id: int,
    ) -> dict[str, object]:
        node = self._get_delivery_address_node_or_404(node_id=node_id)
        location_key = str(node.id)
        provider = "manual"
        cached_node = node
        if cached_node is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="تعذر العثور على عقدة الموقع. حمّل القوائم أولًا ثم أعد المحاولة.",
            )

        zone = (
            self._db.execute(
                select(DeliveryZonePricing).where(DeliveryZonePricing.location_key == location_key)
            )
            .scalars()
            .first()
        )
        now = datetime.now(timezone.utc)
        if zone is None:
            zone = DeliveryZonePricing(
                provider=provider,
                location_key=location_key,
                parent_key=str(node.parent_id) if node.parent_id is not None else None,
                level=cached_node.level,
                external_id=None,
                country_code=cached_node.country_code,
                name=cached_node.name,
                display_name=cached_node.display_name,
                delivery_fee=float(delivery_fee),
                active=bool(active),
                sort_order=int(sort_order),
                created_at=now,
                updated_at=now,
                updated_by=actor_id,
            )
            self._db.add(zone)
            self._db.flush()
            return self._delivery_zone_to_payload(zone, node)

        zone.provider = provider
        zone.parent_key = str(node.parent_id) if node.parent_id is not None else None
        zone.level = cached_node.level
        zone.external_id = None
        zone.country_code = cached_node.country_code
        zone.name = cached_node.name
        zone.display_name = cached_node.display_name
        zone.delivery_fee = float(delivery_fee)
        zone.active = bool(active)
        zone.sort_order = int(sort_order)
        zone.updated_at = now
        zone.updated_by = actor_id
        self._db.flush()
        return self._delivery_zone_to_payload(zone, node)

    def delete_delivery_zone_pricing(self, *, zone_id: int) -> None:
        zone = (
            self._db.execute(select(DeliveryZonePricing).where(DeliveryZonePricing.id == zone_id))
            .scalars()
            .first()
        )
        if zone is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="منطقة التسعير غير موجودة.")
        self._db.delete(zone)
        self._db.flush()

    def quote_delivery_location_pricing(self, *, location_key: str | None) -> dict[str, object]:
        from application.operations_engine.domain.delivery_location_pricing import quote_delivery_location_pricing

        return quote_delivery_location_pricing(self._db, location_key=location_key)

    def update_delivery_policies(
        self,
        *,
        min_order_amount: float,
        auto_notify_team: bool,
        actor_id: int,
    ) -> dict[str, object]:
        return app_update_delivery_policy_settings(
            self._db,
            min_order_amount=min_order_amount,
            auto_notify_team=auto_notify_team,
            actor_id=actor_id,
        )

    def get_operational_capabilities(self) -> dict[str, object]:
        return app_get_operational_capabilities(self._db)

    def _ensure_delivery_location_provider_ready(self, settings: dict[str, object]) -> None:
        if not bool(settings.get("enabled", False)):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="خدمة تحديد مواقع التوصيل غير مفعلة بعد.")
        if not bool(settings.get("geonames_username")):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="اسم مستخدم GeoNames غير مضبوط بعد.")

    def _count_active_delivery_zones(self) -> int:
        return int(
            self._db.execute(
                select(func.count(DeliveryZonePricing.id)).where(
                    DeliveryZonePricing.active.is_(True),
                    DeliveryZonePricing.provider == "manual",
                )
            ).scalar_one()
            or 0
        )

    def _load_delivery_address_child_counts(self, node_ids: list[int]) -> dict[int, int]:
        if not node_ids:
            return {}
        rows = self._db.execute(
            select(
                DeliveryAddressNode.parent_id,
                func.count(DeliveryAddressNode.id),
            )
            .where(DeliveryAddressNode.parent_id.in_(node_ids))
            .group_by(DeliveryAddressNode.parent_id)
        ).all()
        return {int(parent_id): int(count) for parent_id, count in rows if parent_id is not None}

    def _collect_delivery_address_subtree_ids(self, *, root_id: int) -> list[int]:
        subtree_ids: list[int] = []
        frontier = [int(root_id)]

        while frontier:
            subtree_ids.extend(frontier)
            child_rows = self._db.execute(
                select(DeliveryAddressNode.id).where(DeliveryAddressNode.parent_id.in_(frontier))
            ).all()
            frontier = [int(row[0]) for row in child_rows]

        return subtree_ids

    def _load_delivery_address_nodes_by_id(self, node_ids: list[int]) -> dict[int, DeliveryAddressNode]:
        if not node_ids:
            return {}
        items = self._db.execute(
            select(DeliveryAddressNode).where(DeliveryAddressNode.id.in_(node_ids))
        ).scalars().all()
        return {int(item.id): item for item in items}

    def _get_delivery_address_node_or_404(self, *, node_id: int) -> DeliveryAddressNode:
        node = self._db.execute(
            select(DeliveryAddressNode).where(DeliveryAddressNode.id == node_id)
        ).scalars().first()
        if node is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="عقدة العنوان غير موجودة.")
        return node

    def _get_delivery_address_parent_or_validate(
        self,
        *,
        parent_id: int | None,
        expected_level: str,
    ) -> DeliveryAddressNode | None:
        if parent_id is None:
            if expected_level != self.DELIVERY_ADDRESS_LEVELS[0]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="العقدة الجذرية يجب أن تبدأ من المستوى الإداري الأول.",
                )
            return None

        parent = self._get_delivery_address_node_or_404(node_id=parent_id)
        try:
            parent_index = self.DELIVERY_ADDRESS_LEVELS.index(parent.level)
            expected_index = self.DELIVERY_ADDRESS_LEVELS.index(expected_level)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="بنية مستويات العنوان غير صحيحة.") from error
        if expected_index != parent_index + 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="المستوى المختار لا يتبع المستوى الأب بشكل صحيح.",
            )
        return parent

    @staticmethod
    def _delivery_address_to_payload(node: DeliveryAddressNode, child_count: int) -> dict[str, object]:
        return {
            "id": int(node.id),
            "parent_id": int(node.parent_id) if node.parent_id is not None else None,
            "level": node.level,
            "country_code": node.country_code,
            "code": node.code,
            "name": node.name,
            "display_name": node.display_name,
            "postal_code": node.postal_code,
            "notes": node.notes,
            "active": bool(node.active),
            "visible_in_public": bool(node.visible_in_public),
            "sort_order": int(node.sort_order),
            "child_count": int(child_count),
            "can_expand": bool(child_count > 0),
            "created_at": node.created_at,
            "updated_at": node.updated_at,
        }

    @staticmethod
    def _delivery_zone_to_payload(
        zone: DeliveryZonePricing,
        node: DeliveryAddressNode | None,
    ) -> dict[str, object]:
        resolved_node_id = int(node.id) if node is not None else (int(zone.location_key) if str(zone.location_key).isdigit() else 0)
        return {
            "id": int(zone.id),
            "node_id": resolved_node_id,
            "provider": zone.provider,
            "location_key": zone.location_key,
            "parent_key": zone.parent_key,
            "parent_id": int(node.parent_id) if node is not None and node.parent_id is not None else None,
            "level": zone.level,
            "external_id": zone.external_id,
            "country_code": zone.country_code,
            "code": node.code if node is not None else None,
            "name": zone.name,
            "display_name": zone.display_name,
            "delivery_fee": float(zone.delivery_fee),
            "active": bool(zone.active),
            "sort_order": int(zone.sort_order),
            "created_at": zone.created_at,
            "updated_at": zone.updated_at,
        }

    def _get_cached_location_rows(self, *, provider: str, parent_key: str | None) -> list[DeliveryLocationCache]:
        now = datetime.now(timezone.utc)
        return (
            self._db.execute(
                select(DeliveryLocationCache)
                .where(
                    DeliveryLocationCache.provider == provider,
                    DeliveryLocationCache.parent_key.is_(parent_key) if parent_key is None else DeliveryLocationCache.parent_key == parent_key,
                    DeliveryLocationCache.expires_at > now,
                )
                .order_by(DeliveryLocationCache.sort_order.asc(), DeliveryLocationCache.name.asc())
            )
            .scalars()
            .all()
        )

    def _get_cached_location_node(self, *, provider: str, node_key: str) -> DeliveryLocationCache | None:
        now = datetime.now(timezone.utc)
        return (
            self._db.execute(
                select(DeliveryLocationCache).where(
                    DeliveryLocationCache.provider == provider,
                    DeliveryLocationCache.node_key == node_key,
                    DeliveryLocationCache.expires_at > now,
                )
            )
            .scalars()
            .first()
        )

    def _replace_cached_children(
        self,
        *,
        provider: str,
        parent_key: str | None,
        nodes: list[DeliveryLocationNode],
        ttl_hours: int,
    ) -> None:
        existing_rows = (
            self._db.execute(
                select(DeliveryLocationCache).where(
                    DeliveryLocationCache.provider == provider,
                    DeliveryLocationCache.parent_key.is_(parent_key) if parent_key is None else DeliveryLocationCache.parent_key == parent_key,
                )
            )
            .scalars()
            .all()
        )
        for row in existing_rows:
            self._db.delete(row)

        expires_at = datetime.now(timezone.utc).replace(microsecond=0)
        expires_at = expires_at.replace(hour=expires_at.hour)
        from datetime import timedelta
        expires_at = expires_at + timedelta(hours=ttl_hours)

        for node in nodes:
            self._db.add(
                DeliveryLocationCache(
                    provider=provider,
                    node_key=node.key,
                    parent_key=node.parent_key,
                    level=node.level,
                    external_id=node.external_id,
                    country_code=node.country_code,
                    name=node.name,
                    display_name=node.display_name,
                    sort_order=node.sort_order,
                    payload_json=json.dumps(node.payload, ensure_ascii=False),
                    expires_at=expires_at,
                    refreshed_at=datetime.now(timezone.utc),
                )
            )
        self._db.flush()

    @staticmethod
    def _node_to_payload(node: DeliveryLocationNode) -> dict[str, object]:
        return {
            "key": node.key,
            "parent_key": node.parent_key,
            "level": node.level,
            "external_id": node.external_id,
            "country_code": node.country_code,
            "name": node.name,
            "display_name": node.display_name,
            "can_expand": node.can_expand,
        }

    @staticmethod
    def _cache_row_to_payload(row: DeliveryLocationCache) -> dict[str, object]:
        return {
            "key": row.node_key,
            "parent_key": row.parent_key,
            "level": row.level,
            "external_id": row.external_id,
            "country_code": row.country_code,
            "name": row.name,
            "display_name": row.display_name,
            "can_expand": row.level in {"country", "admin_area_level_1", "admin_area_level_2", "locality"},
        }
