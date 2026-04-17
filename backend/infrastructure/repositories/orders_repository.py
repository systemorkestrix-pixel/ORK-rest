from __future__ import annotations

from sqlalchemy import String, asc, cast, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.enums import DeliverySettlementStatus, OrderStatus, OrderType, PaymentStatus
from app.models import DeliverySettlement, Order
from app.schemas import CreateOrderInput
from app.orchestration.service_bridge import (
    app_attach_sent_to_kitchen_at,
    app_create_order,
    get_kitchen_metrics_window,
    kitchen_monitor_summary,
    get_order_polling_ms,
)
from application.operations_engine.domain.order_transitions import (
    transition_order as transition_order_domain,
)


class OrdersRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _extract_order_id_search(value: str) -> int | None:
        digits_only = "".join(char for char in value if char.isdigit())
        if not digits_only:
            return None
        return int(digits_only.lstrip("0") or "0")

    def create_order(
        self,
        *,
        payload: CreateOrderInput,
        created_by: int | None,
        source_actor: str = "system",
    ) -> Order:
        return app_create_order(
            self._db,
            payload=payload,
            created_by=created_by,
            source_actor=source_actor,
        )

    def transition_order(
        self,
        *,
        order_id: int,
        target_status: OrderStatus,
        performed_by: int,
        amount_received: float | None = None,
        collect_payment: bool = True,
        reason_code: str | None = None,
        reason_note: str | None = None,
    ) -> Order:
        return transition_order_domain(
            self._db,
            order_id=order_id,
            target_status=target_status,
            performed_by=performed_by,
            amount_received=amount_received,
            collect_payment=collect_payment,
            reason_code=reason_code,
            reason_note=reason_note,
        )

    def list_orders(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[Order]:
        orders = (
            self._db.execute(
                select(Order)
                .options(joinedload(Order.items))
                .order_by(Order.created_at.desc(), Order.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )
        return app_attach_sent_to_kitchen_at(self._db, orders)

    def list_active_orders(self, *, limit: int) -> list[Order]:
        active_statuses = (
            OrderStatus.CREATED.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.SENT_TO_KITCHEN.value,
            OrderStatus.IN_PREPARATION.value,
            OrderStatus.READY.value,
            OrderStatus.OUT_FOR_DELIVERY.value,
        )
        unsettled_delivery_statuses = (
            DeliverySettlementStatus.PENDING.value,
            DeliverySettlementStatus.PARTIALLY_REMITTED.value,
            DeliverySettlementStatus.REMITTED.value,
            DeliverySettlementStatus.VARIANCE.value,
        )
        delivery_unsettled_condition = (
            (Order.type == OrderType.DELIVERY.value)
            & (Order.status == OrderStatus.DELIVERED.value)
            & (DeliverySettlement.status.in_(unsettled_delivery_statuses))
        )
        dine_in_unsettled_condition = (
            (Order.type == OrderType.DINE_IN.value)
            & (Order.status == OrderStatus.DELIVERED.value)
            & (Order.payment_status != PaymentStatus.PAID.value)
        )
        unresolved_delivery_failure_condition = (
            (Order.type == OrderType.DELIVERY.value)
            & (Order.status == OrderStatus.DELIVERY_FAILED.value)
            & Order.delivery_failure_resolution_status.is_(None)
        )
        orders = (
            self._db.execute(
                select(Order)
                .outerjoin(DeliverySettlement, DeliverySettlement.order_id == Order.id)
                .where(
                    or_(
                        Order.status.in_(active_statuses),
                        delivery_unsettled_condition,
                        dine_in_unsettled_condition,
                        unresolved_delivery_failure_condition,
                    )
                )
                .options(joinedload(Order.items))
                .order_by(Order.created_at.desc(), Order.id.desc())
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )
        return app_attach_sent_to_kitchen_at(self._db, orders)

    def list_orders_paged(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_direction: str,
        status_filter: str | None,
        order_type: str | None,
    ) -> tuple[list[Order], int]:
        conditions = []
        if status_filter is not None:
            conditions.append(Order.status == status_filter)
        if order_type is not None:
            conditions.append(Order.type == order_type)

        normalized_search = (search or "").strip()
        if normalized_search:
            like_value = f"%{normalized_search}%"
            maybe_order_id = self._extract_order_id_search(normalized_search)
            search_terms = [
                cast(Order.id, String).ilike(like_value),
                Order.phone.ilike(like_value),
                Order.address.ilike(like_value),
                Order.notes.ilike(like_value),
                Order.type.ilike(like_value),
                Order.status.ilike(like_value),
            ]
            if maybe_order_id is not None:
                search_terms.append(Order.id == maybe_order_id)
            conditions.append(or_(*search_terms))

        total_stmt = select(func.count(Order.id))
        if conditions:
            total_stmt = total_stmt.where(*conditions)
        total = int(self._db.execute(total_stmt).scalar_one() or 0)

        sort_map = {
            "created_at": Order.created_at,
            "total": Order.total,
            "status": Order.status,
            "id": Order.id,
        }
        sort_column = sort_map.get(sort_by, Order.created_at)
        direction = asc if sort_direction == "asc" else desc

        stmt = select(Order).options(joinedload(Order.items))
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(direction(sort_column), desc(Order.id))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        items = self._db.execute(stmt).unique().scalars().all()
        return app_attach_sent_to_kitchen_at(self._db, items), total

    def list_kitchen_orders(
        self,
        *,
        offset: int,
        limit: int,
        sort_direction: str = "desc",
    ) -> list[Order]:
        visible_statuses = (
            OrderStatus.SENT_TO_KITCHEN.value,
            OrderStatus.IN_PREPARATION.value,
            OrderStatus.READY.value,
        )
        direction = asc if sort_direction == "asc" else desc
        orders = (
            self._db.execute(
                select(Order)
                .where(Order.status.in_(visible_statuses))
                .options(joinedload(Order.items))
                .order_by(direction(Order.created_at), direction(Order.id))
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .scalars()
            .all()
        )
        return app_attach_sent_to_kitchen_at(self._db, orders)

    def list_kitchen_orders_paged(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_direction: str,
        tie_break_direction: str,
        scope: str,
    ) -> tuple[list[Order], int, dict[str, int | float | str]]:
        if scope == "history":
            visible_statuses = (
                OrderStatus.READY.value,
                OrderStatus.OUT_FOR_DELIVERY.value,
                OrderStatus.DELIVERED.value,
                OrderStatus.DELIVERY_FAILED.value,
                OrderStatus.CANCELED.value,
            )
        else:
            visible_statuses = (
                OrderStatus.SENT_TO_KITCHEN.value,
                OrderStatus.IN_PREPARATION.value,
            )
        conditions = [Order.status.in_(visible_statuses)]

        normalized_search = (search or "").strip()
        if normalized_search:
            like_value = f"%{normalized_search}%"
            maybe_order_id = self._extract_order_id_search(normalized_search)
            search_terms = [
                cast(Order.id, String).ilike(like_value),
                Order.type.ilike(like_value),
                Order.status.ilike(like_value),
                Order.phone.ilike(like_value),
                Order.address.ilike(like_value),
                Order.notes.ilike(like_value),
            ]
            if maybe_order_id is not None:
                search_terms.append(Order.id == maybe_order_id)
            conditions.append(or_(*search_terms))

        total = int(self._db.execute(select(func.count(Order.id)).where(*conditions)).scalar_one() or 0)

        sort_map = {
            "created_at": Order.created_at,
            "total": Order.total,
            "status": Order.status,
            "id": Order.id,
        }
        direction = asc if sort_direction == "asc" else desc
        sort_column = sort_map.get(sort_by, Order.created_at)
        secondary_order = asc(Order.id) if tie_break_direction == "asc" else desc(Order.id)

        items = (
            self._db.execute(
                select(Order)
                .where(*conditions)
                .options(joinedload(Order.items))
                .order_by(direction(sort_column), secondary_order)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .unique()
            .scalars()
            .all()
        )
        metrics_window = get_kitchen_metrics_window(self._db)
        summary = kitchen_monitor_summary(self._db, metrics_window=metrics_window)
        return app_attach_sent_to_kitchen_at(self._db, items), total, summary

    def get_kitchen_runtime_settings(self) -> dict[str, int | str]:
        return {
            "order_polling_ms": get_order_polling_ms(self._db),
            "kitchen_metrics_window": get_kitchen_metrics_window(self._db),
        }
