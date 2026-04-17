from __future__ import annotations

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from ..enums import FinancialTransactionType, OrderStatus, OrderType, PaymentStatus
from ..models import DeliverySettlement, Expense, FinancialTransaction, Order, SystemSetting, WarehouseStockBalance


DELIVERY_ACCOUNTING_CUTOVER_AT_KEY = "delivery_accounting_cutover_completed_at"


def _system_setting_exists(db: Session, *, key: str) -> bool:
    return bool(
        db.execute(select(SystemSetting.key).where(SystemSetting.key == key)).scalar_one_or_none()
    )


def assert_financial_invariants(db: Session) -> None:
    cutover_completed = _system_setting_exists(db, key=DELIVERY_ACCOUNTING_CUTOVER_AT_KEY)

    non_delivery_paid_without_sale = int(
        db.execute(
            select(func.count(Order.id))
            .select_from(Order)
            .outerjoin(
                FinancialTransaction,
                and_(
                    FinancialTransaction.order_id == Order.id,
                    FinancialTransaction.type == FinancialTransactionType.SALE.value,
                ),
            )
            .where(
                Order.type != OrderType.DELIVERY.value,
                Order.payment_status.in_((PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value)),
                FinancialTransaction.id.is_(None),
            )
        ).scalar_one()
        or 0
    )
    if non_delivery_paid_without_sale:
        raise RuntimeError(
            f"Financial invariant failed: {non_delivery_paid_without_sale} non-delivery paid/refunded order(s) without sale entry"
        )

    non_delivery_refunded_without_refund_entry = int(
        db.execute(
            select(func.count(Order.id))
            .select_from(Order)
            .outerjoin(
                FinancialTransaction,
                and_(
                    FinancialTransaction.order_id == Order.id,
                    FinancialTransaction.type == FinancialTransactionType.REFUND.value,
                ),
            )
            .where(
                Order.type != OrderType.DELIVERY.value,
                Order.payment_status == PaymentStatus.REFUNDED.value,
                FinancialTransaction.id.is_(None),
            )
        ).scalar_one()
        or 0
    )
    if non_delivery_refunded_without_refund_entry:
        raise RuntimeError(
            f"Financial invariant failed: {non_delivery_refunded_without_refund_entry} non-delivery refunded order(s) without refund entry"
        )

    delivery_scope = [
        Order.type == OrderType.DELIVERY.value,
        Order.status == OrderStatus.DELIVERED.value,
        Order.payment_status.in_((PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value)),
    ]
    if not cutover_completed:
        delivery_scope.append(
            or_(
                Order.accounting_recognized_at.is_not(None),
                exists(select(DeliverySettlement.id).where(DeliverySettlement.order_id == Order.id)),
            )
        )

    delivery_orders_missing_settlement = int(
        db.execute(
            select(func.count(Order.id))
            .select_from(Order)
            .outerjoin(DeliverySettlement, DeliverySettlement.order_id == Order.id)
            .where(*delivery_scope, DeliverySettlement.id.is_(None))
        ).scalar_one()
        or 0
    )
    if delivery_orders_missing_settlement:
        raise RuntimeError(
            f"Financial invariant failed: {delivery_orders_missing_settlement} delivery order(s) without delivery settlement"
        )

    delivery_paid_missing_detailed_entries = int(
        db.execute(
            select(func.count(Order.id))
            .select_from(Order)
            .join(DeliverySettlement, DeliverySettlement.order_id == Order.id)
            .where(
                *delivery_scope,
                Order.payment_status == PaymentStatus.PAID.value,
                ~exists(
                    select(FinancialTransaction.id).where(
                        FinancialTransaction.order_id == Order.id,
                        FinancialTransaction.type == FinancialTransactionType.FOOD_REVENUE.value,
                    )
                ),
            )
        ).scalar_one()
        or 0
    )
    if delivery_paid_missing_detailed_entries:
        raise RuntimeError(
            f"Financial invariant failed: {delivery_paid_missing_detailed_entries} paid delivery order(s) missing detailed revenue entries"
        )

    delivery_refunded_missing_reverse_entries = int(
        db.execute(
            select(func.count(Order.id))
            .select_from(Order)
            .join(DeliverySettlement, DeliverySettlement.order_id == Order.id)
            .where(
                *delivery_scope,
                Order.payment_status == PaymentStatus.REFUNDED.value,
                ~exists(
                    select(FinancialTransaction.id).where(
                        FinancialTransaction.order_id == Order.id,
                        FinancialTransaction.type == FinancialTransactionType.REFUND_FOOD_REVENUE.value,
                    )
                ),
            )
        ).scalar_one()
        or 0
    )
    if delivery_refunded_missing_reverse_entries:
        raise RuntimeError(
            f"Financial invariant failed: {delivery_refunded_missing_reverse_entries} refunded delivery order(s) missing detailed reverse entries"
        )

    approved_expenses_without_entry = int(
        db.execute(
            select(func.count(Expense.id))
            .select_from(Expense)
            .outerjoin(
                FinancialTransaction,
                and_(
                    FinancialTransaction.expense_id == Expense.id,
                    FinancialTransaction.type == FinancialTransactionType.EXPENSE.value,
                ),
            )
            .where(
                Expense.status == "approved",
                FinancialTransaction.id.is_(None),
            )
        ).scalar_one()
        or 0
    )
    if approved_expenses_without_entry:
        raise RuntimeError(
            f"Financial invariant failed: {approved_expenses_without_entry} approved expense(s) without financial entry"
        )

    negative_stock = int(
        db.execute(select(func.count(WarehouseStockBalance.id)).where(WarehouseStockBalance.quantity < 0)).scalar_one() or 0
    )
    if negative_stock:
        raise RuntimeError(f"Financial invariant failed: {negative_stock} stock balance row(s) are negative")
