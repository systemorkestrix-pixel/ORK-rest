from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.enums import FinancialTransactionType, OrderStatus, OrderType, PaymentStatus
from app.models import Order
from application.financial_engine.domain.helpers import normalize_optional_text, record_system_audit


def refund_order(
    db: Session,
    *,
    order_id: int,
    refunded_by: int,
    note: str | None,
    get_order,
    find_latest_order_transaction_by_type,
    reverse_delivery_entries,
    record_financial_entry,
    build_reference_group,
) -> Order:
    normalized_note = normalize_optional_text(note)
    order = get_order(db, order_id)
    is_delivery_order = order.type == OrderType.DELIVERY.value
    if order.status != OrderStatus.DELIVERED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تنفيذ الاسترجاع إلا بعد تسليم الطلب.",
        )

    refund_tx_type = (
        FinancialTransactionType.REFUND_FOOD_REVENUE.value
        if is_delivery_order
        else FinancialTransactionType.REFUND.value
    )
    existing_refund_tx = find_latest_order_transaction_by_type(
        db,
        order_id=int(order.id),
        tx_type=refund_tx_type,
    )
    if existing_refund_tx is not None and order.payment_status == PaymentStatus.REFUNDED.value:
        return order
    if order.payment_status != PaymentStatus.PAID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تنفيذ الاسترجاع لطلب غير مدفوع.",
        )
    order.payment_status = PaymentStatus.REFUNDED.value
    order.paid_by = refunded_by
    order.paid_at = datetime.now(UTC)

    if existing_refund_tx is None:
        if is_delivery_order:
            reverse_delivery_entries(
                db,
                order=order,
                refunded_by=refunded_by,
                note=normalized_note,
            )
        else:
            refund_note = f"استرجاع الطلب #{order.id}"
            if normalized_note:
                refund_note = f"{refund_note} | {normalized_note}"
            record_financial_entry(
                db,
                order_id=int(order.id),
                delivery_settlement_id=None,
                expense_id=None,
                amount=float(order.total or 0.0),
                tx_type=FinancialTransactionType.REFUND.value,
                direction=None,
                account_code=None,
                reference_group=build_reference_group(event_key="order_refund", order_id=int(order.id)),
                created_by=refunded_by,
                note=refund_note,
            )

    record_system_audit(
        db,
        module="financial",
        action="refund_order",
        entity_type="order",
        entity_id=order.id,
        user_id=refunded_by,
        description=f"Refund order #{order.id} for {float(order.total or 0.0):.2f} without warehouse movement.",
    )
    return order
