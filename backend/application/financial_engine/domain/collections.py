from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.enums import FinancialTransactionType, OrderStatus, OrderType, PaymentStatus
from app.models import FinancialTransaction, Order
from application.financial_engine.domain.helpers import record_system_audit

GetOrder = Callable[[Session, int], Order]


def _mark_cash_paid(
    db: Session,
    *,
    order: Order,
    amount_received: float | None,
    user_id: int,
) -> dict[str, float | str | datetime | int]:
    if amount_received is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Amount received is required for cash payment.')
    if amount_received < order.total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Amount received is less than the order total.')

    change_amount = amount_received - order.total
    db.add(
        FinancialTransaction(
            order_id=order.id,
            amount=order.total,
            type=FinancialTransactionType.SALE.value,
            created_by=user_id,
            note='Cash collection on delivery.',
        )
    )
    return {
        'payment_status': PaymentStatus.PAID.value,
        'paid_at': datetime.now(UTC),
        'paid_by': user_id,
        'amount_received': amount_received,
        'change_amount': change_amount,
        'payment_method': 'cash',
    }


def mark_cash_paid(
    db: Session,
    *,
    order: Order,
    amount_received: float | None,
    user_id: int,
) -> dict[str, float | str | datetime | int]:
    return _mark_cash_paid(
        db,
        order=order,
        amount_received=amount_received,
        user_id=user_id,
    )


def collect_order_payment(
    db: Session,
    *,
    order_id: int,
    collected_by: int,
    amount_received: float | None,
    get_order: GetOrder,
    return_payment_values: bool = False,
) -> Order | tuple[Order, dict[str, float | str | datetime | int]]:
    order = get_order(db, order_id)
    if order.type == OrderType.DINE_IN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Dine-in orders must be collected through table session settlement.',
        )
    if order.status != OrderStatus.DELIVERED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only delivered orders can be collected.',
        )
    if order.payment_status == PaymentStatus.PAID.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='This order has already been collected.')

    payment_values = _mark_cash_paid(
        db,
        order=order,
        amount_received=amount_received,
        user_id=collected_by,
    )
    result = db.execute(
        update(Order)
        .where(
            Order.id == order.id,
            Order.status == OrderStatus.DELIVERED.value,
            Order.payment_status != PaymentStatus.PAID.value,
        )
        .values(**payment_values)
    )
    if result.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='A concurrent update prevented payment collection. Please retry.',
        )

    collected_amount = float(payment_values.get('amount_received') or order.total)
    record_system_audit(
        db,
        module='financial',
        action='collect_order_payment',
        entity_type='order',
        entity_id=order.id,
        user_id=collected_by,
        description=f'Collected order #{order.id} with received amount {collected_amount:.2f}.',
    )

    db.flush()
    db.commit()
    refreshed_order = get_order(db, order_id)
    if return_payment_values:
        return refreshed_order, payment_values
    return refreshed_order
