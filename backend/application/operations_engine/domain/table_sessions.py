from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.enums import (
    CollectionChannel,
    FinancialTransactionType,
    OrderStatus,
    OrderType,
    PaymentStatus,
    TableStatus,
)
from app.models import FinancialTransaction, Order, RestaurantTable
from app.tenant_runtime import infer_tenant_code_from_session
from application.master_engine.domain.provisioning import build_tenant_table_public_path
from application.operations_engine.domain.helpers import record_system_audit

TERMINAL_ORDER_STATUSES = (
    OrderStatus.DELIVERED.value,
    OrderStatus.CANCELED.value,
    OrderStatus.DELIVERY_FAILED.value,
)


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


def _table_session_open_condition():
    return or_(
        Order.status.notin_(TERMINAL_ORDER_STATUSES),
        and_(
            Order.status == OrderStatus.DELIVERED.value,
            Order.payment_status != PaymentStatus.PAID.value,
        ),
    )


def _list_open_table_session_orders_for_tables(
    db: Session,
    *,
    table_ids: list[int] | None = None,
) -> list[Order]:
    stmt = (
        select(Order)
        .where(
            Order.table_id.is_not(None),
            Order.type == OrderType.DINE_IN.value,
            _table_session_open_condition(),
        )
        .options(joinedload(Order.items))
        .order_by(Order.table_id.asc(), Order.created_at.desc(), Order.id.desc())
    )
    if table_ids is not None:
        if not table_ids:
            return []
        stmt = stmt.where(Order.table_id.in_(table_ids))
    return db.execute(stmt).unique().scalars().all()


def _list_open_table_session_orders(db: Session, *, table_id: int) -> list[Order]:
    return _list_open_table_session_orders_for_tables(db, table_ids=[table_id])


def _compute_table_session_snapshot(table: RestaurantTable, orders: list[Order]) -> dict[str, object]:
    active_orders_count = sum(1 for order in orders if order.status not in TERMINAL_ORDER_STATUSES)
    unsettled_orders_count = sum(1 for order in orders if order.payment_status != PaymentStatus.PAID.value)
    unpaid_total = sum(float(order.total or 0) for order in orders if order.payment_status != PaymentStatus.PAID.value)
    return {
        "table": table,
        "has_active_session": len(orders) > 0,
        "total_orders": len(orders),
        "active_orders_count": active_orders_count,
        "unsettled_orders_count": unsettled_orders_count,
        "unpaid_total": unpaid_total,
        "latest_order_status": orders[0].status if orders else None,
        "orders": orders,
    }


def get_table_or_404(db: Session, table_id: int) -> RestaurantTable:
    table = db.execute(select(RestaurantTable).where(RestaurantTable.id == table_id)).scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطاولة غير موجودة.")
    return table


def create_table(db: Session, *, status_value: TableStatus) -> RestaurantTable:
    tenant_code = infer_tenant_code_from_session(db)
    table = RestaurantTable(
        qr_code=f"/menu?seed={uuid4()}",
        status=status_value.value,
    )
    db.add(table)
    db.flush()
    table.qr_code = build_tenant_table_public_path(tenant_code=tenant_code, table_id=int(table.id))
    return get_table_or_404(db, table.id)


def update_table(db: Session, *, table_id: int, status_value: TableStatus) -> RestaurantTable:
    table = get_table_or_404(db, table_id)
    session = get_table_session_snapshot(db, table_id=table_id)
    if session["has_active_session"] and status_value in (TableStatus.AVAILABLE, TableStatus.RESERVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تغيير حالة الطاولة مع وجود جلسة نشطة. قم بإغلاق الجلسة أو تسويتها أولاً.",
        )
    table.status = status_value.value
    return get_table_or_404(db, table_id)


def delete_table(db: Session, *, table_id: int) -> None:
    table = get_table_or_404(db, table_id)
    has_orders = (
        db.execute(select(Order.id).where(Order.table_id == table_id).limit(1)).scalar_one_or_none() is not None
    )
    if has_orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن حذف الطاولة لأنها مرتبطة بطلبات سابقة.",
        )
    db.delete(table)


def refresh_table_occupancy_state(db: Session, *, table_id: int) -> None:
    table = db.execute(select(RestaurantTable).where(RestaurantTable.id == table_id)).scalar_one_or_none()
    if not table:
        return
    has_open_session = (
        db.execute(
            select(Order.id)
            .where(
                Order.table_id == table_id,
                Order.type == OrderType.DINE_IN.value,
                _table_session_open_condition(),
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )
    if has_open_session:
        table.status = TableStatus.OCCUPIED.value
    elif table.status == TableStatus.OCCUPIED.value:
        table.status = TableStatus.AVAILABLE.value


def list_tables_with_session_summary(
    db: Session,
    *,
    table_ids: list[int] | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, object]]:
    safe_offset, safe_limit = _normalize_offset_limit(offset=offset, limit=limit, max_limit=500)
    stmt = select(RestaurantTable).order_by(RestaurantTable.id.asc())
    if table_ids is not None:
        normalized_ids = sorted({int(table_id) for table_id in table_ids if int(table_id) > 0})
        if not normalized_ids:
            return []
        stmt = stmt.where(RestaurantTable.id.in_(normalized_ids))
    elif safe_limit is not None:
        stmt = stmt.offset(safe_offset).limit(safe_limit)

    tables = db.execute(stmt).scalars().all()
    if not tables:
        return []

    table_ids = [int(table.id) for table in tables]
    total_orders_rows = db.execute(
        select(
            Order.table_id.label("table_id"),
            func.count(Order.id).label("total_orders_count"),
        )
        .where(Order.table_id.in_(table_ids))
        .group_by(Order.table_id)
    ).all()
    total_orders_count_map = {
        int(row.table_id): int(row.total_orders_count or 0)
        for row in total_orders_rows
        if row.table_id is not None
    }

    session_rows = db.execute(
        select(
            Order.table_id.label("table_id"),
            func.count(Order.id).label("session_orders_count"),
            func.sum(case((Order.status.notin_(TERMINAL_ORDER_STATUSES), 1), else_=0)).label("active_orders_count"),
            func.sum(case((Order.payment_status != PaymentStatus.PAID.value, 1), else_=0)).label("unsettled_orders_count"),
            func.sum(case((Order.payment_status != PaymentStatus.PAID.value, Order.total), else_=0.0)).label("unpaid_total"),
        )
        .where(
            Order.table_id.in_(table_ids),
            Order.type == OrderType.DINE_IN.value,
            _table_session_open_condition(),
        )
        .group_by(Order.table_id)
    ).all()
    session_map: dict[int, dict[str, float | int]] = {}
    for row in session_rows:
        if row.table_id is None:
            continue
        table_id = int(row.table_id)
        session_map[table_id] = {
            "session_orders_count": int(row.session_orders_count or 0),
            "active_orders_count": int(row.active_orders_count or 0),
            "unsettled_orders_count": int(row.unsettled_orders_count or 0),
            "unpaid_total": float(row.unpaid_total or 0.0),
        }

    rows: list[dict[str, object]] = []
    for table in tables:
        session = session_map.get(int(table.id), None)
        total_orders_count = int(total_orders_count_map.get(int(table.id), 0))
        rows.append(
            {
                "id": table.id,
                "qr_code": table.qr_code,
                "status": table.status,
                "total_orders_count": total_orders_count,
                "has_active_session": bool(session is not None and int(session["session_orders_count"]) > 0),
                "active_orders_count": int(session["active_orders_count"]) if session is not None else 0,
                "unsettled_orders_count": int(session["unsettled_orders_count"]) if session is not None else 0,
                "unpaid_total": float(session["unpaid_total"]) if session is not None else 0.0,
            }
        )
    return rows


def get_table_session_snapshot(db: Session, *, table_id: int) -> dict[str, object]:
    table = get_table_or_404(db, table_id)
    orders = _list_open_table_session_orders(db, table_id=table_id)
    return _compute_table_session_snapshot(table, orders)


def list_active_table_sessions(
    db: Session,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, object]]:
    safe_offset, safe_limit = _normalize_offset_limit(offset=offset, limit=limit, max_limit=500)
    if safe_offset > 0 or safe_limit is not None:
        latest_created_at = func.max(Order.created_at).label("latest_created_at")
        latest_order_id = func.max(Order.id).label("latest_order_id")
        table_ids_stmt = (
            select(Order.table_id.label("table_id"), latest_created_at, latest_order_id)
            .where(
                Order.table_id.is_not(None),
                Order.type == OrderType.DINE_IN.value,
                _table_session_open_condition(),
            )
            .group_by(Order.table_id)
            .order_by(latest_created_at.desc(), latest_order_id.desc())
            .offset(safe_offset)
        )
        if safe_limit is not None:
            table_ids_stmt = table_ids_stmt.limit(safe_limit)
        table_id_rows = db.execute(table_ids_stmt).all()
        table_ids = [int(row.table_id) for row in table_id_rows if row.table_id is not None]
        if not table_ids:
            return []
        session_orders = _list_open_table_session_orders_for_tables(db, table_ids=table_ids)
    else:
        session_orders = _list_open_table_session_orders_for_tables(db)

    if not session_orders:
        return []

    table_ids = sorted({int(order.table_id) for order in session_orders if order.table_id is not None})
    tables = db.execute(select(RestaurantTable).where(RestaurantTable.id.in_(table_ids))).scalars().all()
    table_map = {int(table.id): table for table in tables}

    orders_by_table_id: dict[int, list[Order]] = {}
    for order in session_orders:
        if order.table_id is None:
            continue
        orders_by_table_id.setdefault(int(order.table_id), []).append(order)

    sessions = [
        _compute_table_session_snapshot(table_map[table_id], orders_by_table_id.get(table_id, []))
        for table_id in table_ids
        if table_id in table_map
    ]
    sessions.sort(
        key=lambda session: (
            session["orders"][0].created_at if session["orders"] else datetime.min,
            session["orders"][0].id if session["orders"] else 0,
        ),
        reverse=True,
    )
    return sessions


def settle_table_session(
    db: Session,
    *,
    table_id: int,
    performed_by: int,
    amount_received: float | None = None,
) -> dict[str, object]:
    table = get_table_or_404(db, table_id)
    session_orders = _list_open_table_session_orders(db, table_id=table_id)
    if not session_orders:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا توجد جلسة نشطة لهذه الطاولة.")

    blocking_orders = [order for order in session_orders if order.status != OrderStatus.DELIVERED.value]
    if blocking_orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تسوية الجلسة قبل اكتمال جميع الطلبات.",
        )

    unpaid_orders = [order for order in session_orders if order.payment_status != PaymentStatus.PAID.value]
    settled_total = sum(float(order.total or 0) for order in unpaid_orders)
    received = settled_total if amount_received is None else float(amount_received)

    if received < settled_total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المبلغ المستلم أقل من إجمالي الجلسة.")

    now = datetime.now(UTC)
    unpaid_order_ids = [order.id for order in unpaid_orders]
    existing_sale_order_ids = (
        set(
            db.execute(
                select(FinancialTransaction.order_id).where(
                    FinancialTransaction.order_id.in_(unpaid_order_ids),
                    FinancialTransaction.type == FinancialTransactionType.SALE.value,
                )
            ).scalars().all()
        )
        if unpaid_order_ids
        else set()
    )

    settled_order_ids: list[int] = []
    for order in unpaid_orders:
        order.payment_status = PaymentStatus.PAID.value
        order.paid_at = now
        order.paid_by = performed_by
        order.amount_received = order.total
        order.change_amount = 0.0
        order.payment_method = "cash"
        order.collected_by_channel = CollectionChannel.CASHIER.value
        order.collection_variance_amount = 0.0
        order.collection_variance_reason = None
        order.accounting_recognized_at = now
        settled_order_ids.append(order.id)

        if order.id not in existing_sale_order_ids:
            db.add(
                FinancialTransaction(
                    order_id=order.id,
                    amount=order.total,
                    type=FinancialTransactionType.SALE.value,
                    created_by=performed_by,
                    note=f"تحصيل جلسة الطاولة رقم {table.id}",
                )
            )

    table.status = TableStatus.AVAILABLE.value
    change_amount = received - settled_total
    record_system_audit(
        db,
        module="tables",
        action="settle_table_session",
        entity_type="table",
        entity_id=table_id,
        user_id=performed_by,
        description=(
            f"تسوية جلسة الطاولة #{table_id} بعدد {len(settled_order_ids)} "
            f"طلبات بإجمالي {settled_total:.2f} د.ج."
        ),
    )

    return {
        "table_id": table_id,
        "settled_order_ids": settled_order_ids,
        "settled_total": settled_total,
        "amount_received": received,
        "change_amount": change_amount,
        "table_status": TableStatus.AVAILABLE.value,
    }
