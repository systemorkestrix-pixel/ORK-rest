from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.enums import ProductKind
from app.models import (
    OrderCostEntry,
    OrderItem,
    Product,
    ProductCategory,
    ProductConsumptionComponent,
    ProductSecondaryLink,
    WarehouseItem,
)

PROTECTED_PRODUCT_CATEGORY_NAMES = {"عام"}
PROTECTED_PRODUCT_CATEGORY_NAMES_LOWER = {item.lower() for item in PROTECTED_PRODUCT_CATEGORY_NAMES}


def _normalize_offset_limit(
    *,
    offset: int = 0,
    limit: int | None = None,
    max_limit: int = 500,
) -> tuple[int, int | None]:
    safe_offset = max(0, int(offset))
    if limit is None:
        return safe_offset, None
    safe_limit = max(1, min(int(limit), max_limit))
    return safe_offset, safe_limit


def normalize_category_name(name: str) -> str:
    normalized = " ".join(name.split()).strip()
    if len(normalized) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم التصنيف غير صالح.")
    return normalized


def is_protected_product_category(name: str) -> bool:
    return normalize_category_name(name).lower() in PROTECTED_PRODUCT_CATEGORY_NAMES_LOWER


def _product_load_stmt():
    return select(Product).options(
        selectinload(Product.secondary_links).selectinload(ProductSecondaryLink.secondary_product),
        selectinload(Product.consumption_components).selectinload(ProductConsumptionComponent.warehouse_item),
    )


def get_product_category_or_404(db: Session, category_id: int) -> ProductCategory:
    category = db.execute(select(ProductCategory).where(ProductCategory.id == category_id)).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="التصنيف غير موجود.")
    return category


def get_or_create_secondary_product_category(db: Session) -> ProductCategory:
    category = db.execute(
        select(ProductCategory)
        .where(ProductCategory.name.in_(tuple(PROTECTED_PRODUCT_CATEGORY_NAMES)))
        .order_by(ProductCategory.sort_order.asc(), ProductCategory.id.asc())
    ).scalar_one_or_none()
    if category is not None:
        if not category.active:
            category.active = True
            db.flush()
        return category

    next_sort_order = int(db.execute(select(func.coalesce(func.max(ProductCategory.sort_order), -1))).scalar_one() or -1) + 1
    category = ProductCategory(name="عام", active=True, sort_order=next_sort_order)
    db.add(category)
    db.flush()
    return category


def resolve_product_category(
    db: Session,
    *,
    kind: ProductKind,
    category_id: int | None,
) -> ProductCategory:
    if kind == ProductKind.SECONDARY:
        return get_or_create_secondary_product_category(db)

    if category_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر تصنيفًا صالحًا للمنتج الأساسي.")

    category = get_product_category_or_404(db, category_id)
    if not category.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="التصنيف غير نشط.")
    return category


def get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.execute(_product_load_stmt().where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المنتج غير موجود.")
    return product


def _coerce_secondary_link_rows(rows: Sequence[object] | None) -> list[dict[str, object]]:
    if rows is None:
        return []
    normalized_rows: list[dict[str, object]] = []
    for row in rows:
        normalized_rows.append(
            {
                "secondary_product_id": int(getattr(row, "secondary_product_id")),
                "sort_order": int(getattr(row, "sort_order", 0) or 0),
                "is_default": bool(getattr(row, "is_default", False)),
                "max_quantity": int(getattr(row, "max_quantity", 1) or 1),
            }
        )
    return normalized_rows


def _coerce_consumption_rows(rows: Sequence[object] | None) -> list[dict[str, object]]:
    if rows is None:
        return []
    normalized_rows: list[dict[str, object]] = []
    for row in rows:
        normalized_rows.append(
            {
                "warehouse_item_id": int(getattr(row, "warehouse_item_id")),
                "quantity_per_unit": float(getattr(row, "quantity_per_unit")),
            }
        )
    return normalized_rows


def _validate_secondary_targets(
    db: Session,
    *,
    product_id: int,
    kind: ProductKind,
    secondary_links: Sequence[dict[str, object]],
) -> None:
    if kind != ProductKind.PRIMARY:
        if secondary_links:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="يمكن ربط المنتجات الثانوية فقط بالمنتج الأساسي.",
            )
        return
    target_ids = [int(row["secondary_product_id"]) for row in secondary_links]
    if not target_ids:
        return
    if len(target_ids) != len(set(target_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن تكرار نفس المنتج الثانوي.")
    if any(target_id == product_id for target_id in target_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن ربط المنتج بنفسه كمنتج ثانوي.")
    rows = db.execute(
        select(Product.id).where(
            Product.id.in_(target_ids),
            Product.kind == ProductKind.SECONDARY.value,
            Product.is_archived.is_(False),
        )
    ).all()
    valid_ids = {int(row.id) for row in rows}
    missing = [target_id for target_id in target_ids if target_id not in valid_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"هذه المنتجات الثانوية غير صالحة أو مؤرشفة: {missing}",
        )


def _validate_consumption_targets(
    db: Session,
    *,
    consumption_components: Sequence[dict[str, object]],
) -> None:
    item_ids = [int(row["warehouse_item_id"]) for row in consumption_components]
    if not item_ids:
        return
    if len(item_ids) != len(set(item_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن تكرار نفس صنف المستودع.")
    rows = db.execute(
        select(WarehouseItem.id).where(
            WarehouseItem.id.in_(item_ids),
            WarehouseItem.active.is_(True),
        )
    ).all()
    valid_ids = {int(row.id) for row in rows}
    missing = [item_id for item_id in item_ids if item_id not in valid_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"هذه الأصناف غير موجودة أو غير نشطة في المستودع: {missing}",
        )


def _replace_secondary_links(product: Product, *, secondary_links: Sequence[dict[str, object]]) -> None:
    product.secondary_links.clear()
    for row in secondary_links:
        product.secondary_links.append(
            ProductSecondaryLink(
                secondary_product_id=int(row["secondary_product_id"]),
                sort_order=int(row["sort_order"]),
                is_default=bool(row["is_default"]),
                max_quantity=int(row["max_quantity"]),
            )
        )


def _replace_consumption_components(
    product: Product,
    *,
    consumption_components: Sequence[dict[str, object]],
) -> None:
    product.consumption_components.clear()
    for row in consumption_components:
        product.consumption_components.append(
            ProductConsumptionComponent(
                warehouse_item_id=int(row["warehouse_item_id"]),
                quantity_per_unit=float(row["quantity_per_unit"]),
            )
        )


def _assert_kind_change_is_allowed(db: Session, *, product_id: int, next_kind: ProductKind) -> None:
    if next_kind == ProductKind.SECONDARY:
        return
    incoming_links = int(
        db.execute(
            select(func.count(ProductSecondaryLink.id)).where(ProductSecondaryLink.secondary_product_id == product_id)
        ).scalar_one()
        or 0
    )
    if incoming_links > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تغيير نوع المنتج لوجود روابط منتجات ثانوية قائمة عليه.",
        )


def list_product_categories(
    db: Session,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[ProductCategory]:
    safe_offset, safe_limit = _normalize_offset_limit(offset=offset, limit=limit, max_limit=500)
    stmt = (
        select(ProductCategory)
        .order_by(ProductCategory.sort_order.asc(), ProductCategory.id.asc())
        .offset(safe_offset)
    )
    if safe_limit is not None:
        stmt = stmt.limit(safe_limit)
    return db.execute(stmt).scalars().all()


def create_product_category(
    db: Session,
    *,
    name: str,
    active: bool,
    sort_order: int,
) -> ProductCategory:
    normalized_name = normalize_category_name(name)
    existing = db.execute(
        select(ProductCategory).where(func.lower(ProductCategory.name) == normalized_name.lower())
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم التصنيف مستخدم مسبقًا.")

    category = ProductCategory(name=normalized_name, active=active, sort_order=sort_order)
    db.add(category)
    return category


def update_product_category(
    db: Session,
    *,
    category_id: int | None,
    name: str,
    active: bool,
    sort_order: int,
) -> ProductCategory:
    if category_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="التصنيف غير موجود.")

    category = get_product_category_or_404(db, category_id)
    if is_protected_product_category(category.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تعديل التصنيف الافتراضي.",
        )

    normalized_name = normalize_category_name(name)
    existing = db.execute(
        select(ProductCategory).where(
            func.lower(ProductCategory.name) == normalized_name.lower(),
            ProductCategory.id != category_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اسم التصنيف مستخدم مسبقًا.")

    category.name = normalized_name
    category.active = active
    category.sort_order = sort_order
    db.execute(
        update(Product)
        .where(Product.category_id == category_id)
        .values(category=normalized_name)
    )
    if not active:
        db.execute(
            update(Product)
            .where(Product.category_id == category_id)
            .values(available=False)
        )
    return category


def delete_product_category(db: Session, *, category_id: int) -> None:
    category = get_product_category_or_404(db, category_id)
    if is_protected_product_category(category.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن حذف التصنيف الافتراضي.",
        )

    linked_products = db.execute(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    ).scalar_one()
    if int(linked_products or 0) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن حذف التصنيف لوجود منتجات مرتبطة.")

    db.delete(category)


def create_product(
    db: Session,
    *,
    name: str,
    description: str | None,
    price: float,
    kind: ProductKind,
    available: bool,
    category_id: int | None,
    secondary_links: Sequence[object] | None,
    consumption_components: Sequence[object] | None,
) -> Product:
    category = resolve_product_category(db, kind=kind, category_id=category_id)

    normalized_secondary_links = _coerce_secondary_link_rows(secondary_links)
    normalized_consumption_components = _coerce_consumption_rows(consumption_components)

    product = Product(
        name=name,
        description=description,
        price=price,
        kind=kind.value,
        available=available,
        category=category.name,
        category_id=category.id,
        is_archived=False,
    )
    db.add(product)
    db.flush()

    _validate_secondary_targets(
        db,
        product_id=int(product.id),
        kind=kind,
        secondary_links=normalized_secondary_links,
    )
    _validate_consumption_targets(db, consumption_components=normalized_consumption_components)

    if kind == ProductKind.PRIMARY:
        _replace_secondary_links(product, secondary_links=normalized_secondary_links)
    _replace_consumption_components(product, consumption_components=normalized_consumption_components)

    db.flush()
    return get_product_or_404(db, int(product.id))


def update_product(
    db: Session,
    *,
    product_id: int,
    name: str,
    description: str | None,
    price: float,
    kind: ProductKind,
    available: bool,
    category_id: int | None,
    secondary_links: Sequence[object] | None,
    consumption_components: Sequence[object] | None,
    is_archived: bool | None,
) -> Product:
    category = resolve_product_category(db, kind=kind, category_id=category_id)

    product = get_product_or_404(db, product_id)
    _assert_kind_change_is_allowed(db, product_id=product_id, next_kind=kind)

    normalized_secondary_links = _coerce_secondary_link_rows(secondary_links)
    normalized_consumption_components = _coerce_consumption_rows(consumption_components)
    if secondary_links is not None:
        _validate_secondary_targets(
            db,
            product_id=product_id,
            kind=kind,
            secondary_links=normalized_secondary_links,
        )
    if consumption_components is not None:
        _validate_consumption_targets(db, consumption_components=normalized_consumption_components)

    product.name = name
    product.description = description
    product.price = price
    product.kind = kind.value
    product.available = available
    product.category = category.name
    product.category_id = category.id
    if is_archived is not None:
        product.is_archived = is_archived
    if product.is_archived:
        product.available = False

    if kind != ProductKind.PRIMARY:
        if product.secondary_links:
            product.secondary_links.clear()
            db.flush()
    elif secondary_links is not None:
        if product.secondary_links:
            product.secondary_links.clear()
            db.flush()
        _replace_secondary_links(product, secondary_links=normalized_secondary_links)

    if consumption_components is not None:
        if product.consumption_components:
            product.consumption_components.clear()
            db.flush()
        _replace_consumption_components(product, consumption_components=normalized_consumption_components)

    db.flush()
    return get_product_or_404(db, product_id)


def archive_product(db: Session, *, product_id: int) -> None:
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المنتج غير موجود.")

    product.is_archived = True
    product.available = False


def delete_product_permanently(db: Session, *, product_id: int) -> str | None:
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المنتج غير موجود.")
    if not bool(product.is_archived):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن حذف منتج غير مؤرشف. قم بأرشفته أولًا.",
        )

    linked_order_items = int(
        db.execute(select(func.count(OrderItem.id)).where(OrderItem.product_id == product_id)).scalar_one()
        or 0
    )
    linked_cost_entries = int(
        db.execute(select(func.count(OrderCostEntry.id)).where(OrderCostEntry.product_id == product_id)).scalar_one()
        or 0
    )
    if linked_order_items > 0 or linked_cost_entries > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن حذف المنتج لوجود طلبات أو تكاليف مرتبطة.",
        )

    image_path = product.image_path
    db.delete(product)
    return image_path
