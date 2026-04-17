from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    CollectionChannel,
    DeliverySettlementStatus,
    DriverShareModel,
    FinancialTransactionDirection,
    FinancialTransactionType,
    PaymentStatus,
)
from app.models import DeliveryAssignment, DeliveryDriver, DeliverySettlement, Order
from app.repositories.financial_repository import create_financial_transaction


def build_reference_group(*, event_key: str, order_id: int) -> str:
    return f"{event_key}:order:{order_id}:{uuid4().hex[:12]}"


def record_financial_entry(
    db: Session,
    *,
    order_id: int | None,
    delivery_settlement_id: int | None,
    expense_id: int | None,
    amount: float,
    tx_type: str,
    direction: str | None,
    account_code: str | None,
    reference_group: str | None,
    created_by: int,
    note: str | None,
) -> None:
    create_financial_transaction(
        db,
        order_id=order_id,
        delivery_settlement_id=delivery_settlement_id,
        expense_id=expense_id,
        amount=float(amount),
        tx_type=tx_type,
        direction=direction,
        account_code=account_code,
        reference_group=reference_group,
        created_by=created_by,
        note=note,
    )


def resolve_driver_share(driver: DeliveryDriver, *, delivery_fee: float) -> tuple[str, float, float]:
    safe_delivery_fee = max(0.0, float(delivery_fee))
    return DriverShareModel.FULL_DELIVERY_FEE.value, safe_delivery_fee, round(safe_delivery_fee, 2)


def create_delivery_detailed_entries(
    db: Session,
    *,
    order: Order,
    settlement: DeliverySettlement,
    created_by: int,
    reference_group: str,
    note_prefix: str,
) -> None:
    order_id = int(order.id)
    settlement_id = int(settlement.id)
    record_financial_entry(
        db,
        order_id=order_id,
        delivery_settlement_id=settlement_id,
        expense_id=None,
        amount=float(settlement.food_revenue_amount),
        tx_type=FinancialTransactionType.FOOD_REVENUE.value,
        direction=FinancialTransactionDirection.CREDIT.value,
        account_code="REV_FOOD",
        reference_group=reference_group,
        created_by=created_by,
        note=f"{note_prefix} | Food revenue",
    )
    record_financial_entry(
        db,
        order_id=order_id,
        delivery_settlement_id=settlement_id,
        expense_id=None,
        amount=float(settlement.delivery_revenue_amount),
        tx_type=FinancialTransactionType.DELIVERY_REVENUE.value,
        direction=FinancialTransactionDirection.CREDIT.value,
        account_code="REV_DELIVERY",
        reference_group=reference_group,
        created_by=created_by,
        note=f"{note_prefix} | Delivery revenue",
    )
    record_financial_entry(
        db,
        order_id=order_id,
        delivery_settlement_id=settlement_id,
        expense_id=None,
        amount=float(settlement.driver_due_amount),
        tx_type=FinancialTransactionType.DRIVER_PAYABLE.value,
        direction=FinancialTransactionDirection.CREDIT.value,
        account_code="LIAB_DRIVER_PAYABLE",
        reference_group=reference_group,
        created_by=created_by,
        note=f"{note_prefix} | Driver payable",
    )
    record_financial_entry(
        db,
        order_id=order_id,
        delivery_settlement_id=settlement_id,
        expense_id=None,
        amount=float(settlement.actual_collected_amount),
        tx_type=FinancialTransactionType.COLLECTION_CLEARING.value,
        direction=FinancialTransactionDirection.DEBIT.value,
        account_code="ASSET_COLLECTION_CLEARING",
        reference_group=reference_group,
        created_by=created_by,
        note=f"{note_prefix} | Driver collection clearing",
    )
    if abs(float(settlement.variance_amount or 0.0)) > 0.009:
        variance_amount = abs(float(settlement.variance_amount))
        variance_direction = (
            FinancialTransactionDirection.CREDIT.value
            if settlement.variance_amount > 0
            else FinancialTransactionDirection.DEBIT.value
        )
        record_financial_entry(
            db,
            order_id=order_id,
            delivery_settlement_id=settlement_id,
            expense_id=None,
            amount=variance_amount,
            tx_type=FinancialTransactionType.COLLECTION_ADJUSTMENT.value,
            direction=variance_direction,
            account_code="ADJ_COLLECTION_VARIANCE",
            reference_group=reference_group,
            created_by=created_by,
            note=f"{note_prefix} | Delivery collection variance",
        )


def reverse_delivery_detailed_entries(
    db: Session,
    *,
    order: Order,
    refunded_by: int,
    note: str | None,
) -> None:
    settlement = db.execute(
        select(DeliverySettlement).where(DeliverySettlement.order_id == int(order.id))
    ).scalar_one_or_none()
    if settlement is None:
        return

    reference_group = build_reference_group(event_key="delivery_refund", order_id=int(order.id))
    note_prefix = f"Delivery refund for order #{order.id}"
    if note:
        note_prefix = f"{note_prefix} | {note}"
    record_financial_entry(
        db,
        order_id=int(order.id),
        delivery_settlement_id=int(settlement.id),
        expense_id=None,
        amount=float(settlement.food_revenue_amount),
        tx_type=FinancialTransactionType.REFUND_FOOD_REVENUE.value,
        direction=FinancialTransactionDirection.DEBIT.value,
        account_code="REV_FOOD",
        reference_group=reference_group,
        created_by=refunded_by,
        note=f"{note_prefix} | Reverse food revenue",
    )
    record_financial_entry(
        db,
        order_id=int(order.id),
        delivery_settlement_id=int(settlement.id),
        expense_id=None,
        amount=float(settlement.delivery_revenue_amount),
        tx_type=FinancialTransactionType.REFUND_DELIVERY_REVENUE.value,
        direction=FinancialTransactionDirection.DEBIT.value,
        account_code="REV_DELIVERY",
        reference_group=reference_group,
        created_by=refunded_by,
        note=f"{note_prefix} | Reverse delivery revenue",
    )
    record_financial_entry(
        db,
        order_id=int(order.id),
        delivery_settlement_id=int(settlement.id),
        expense_id=None,
        amount=float(settlement.driver_due_amount),
        tx_type=FinancialTransactionType.REVERSE_DRIVER_PAYABLE.value,
        direction=FinancialTransactionDirection.DEBIT.value,
        account_code="LIAB_DRIVER_PAYABLE",
        reference_group=reference_group,
        created_by=refunded_by,
        note=f"{note_prefix} | Reverse driver payable",
    )
    record_financial_entry(
        db,
        order_id=int(order.id),
        delivery_settlement_id=int(settlement.id),
        expense_id=None,
        amount=float(settlement.actual_collected_amount),
        tx_type=FinancialTransactionType.REVERSE_COLLECTION_CLEARING.value,
        direction=FinancialTransactionDirection.CREDIT.value,
        account_code="ASSET_COLLECTION_CLEARING",
        reference_group=reference_group,
        created_by=refunded_by,
        note=f"{note_prefix} | Reverse collection clearing",
    )
    if abs(float(settlement.variance_amount or 0.0)) > 0.009:
        variance_amount = abs(float(settlement.variance_amount))
        variance_direction = (
            FinancialTransactionDirection.DEBIT.value
            if settlement.variance_amount > 0
            else FinancialTransactionDirection.CREDIT.value
        )
        record_financial_entry(
            db,
            order_id=int(order.id),
            delivery_settlement_id=int(settlement.id),
            expense_id=None,
            amount=variance_amount,
            tx_type=FinancialTransactionType.REVERSE_COLLECTION_ADJUSTMENT.value,
            direction=variance_direction,
            account_code="ADJ_COLLECTION_VARIANCE",
            reference_group=reference_group,
            created_by=refunded_by,
            note=f"{note_prefix} | Reverse collection variance",
        )


def record_delivery_completion(
    db: Session,
    *,
    order: Order,
    assignment: DeliveryAssignment,
    driver: DeliveryDriver,
    amount_received: float | None,
    actor_id: int,
) -> dict[str, float | str | datetime | int | None]:
    existing_settlement = db.execute(
        select(DeliverySettlement).where(DeliverySettlement.order_id == int(order.id))
    ).scalar_one_or_none()
    if existing_settlement is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="تم تسجيل التسوية المالية لهذا الطلب مسبقاً.",
        )

    actual_collected_amount = float(order.total if amount_received is None else amount_received)
    if actual_collected_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="المبلغ المستلم الفعلي يجب أن يكون أكبر من صفر.",
        )

    now = datetime.now(UTC)
    variance_amount = round(actual_collected_amount - float(order.total or 0.0), 2)
    driver_share_model, driver_share_value, driver_due_amount = resolve_driver_share(
        driver,
        delivery_fee=float(order.delivery_fee or 0.0),
    )
    store_due_amount = round(actual_collected_amount - driver_due_amount, 2)
    settlement_status = (
        DeliverySettlementStatus.VARIANCE.value
        if abs(variance_amount) > 0.009
        else DeliverySettlementStatus.PENDING.value
    )
    settlement = DeliverySettlement(
        order_id=int(order.id),
        assignment_id=int(assignment.id),
        driver_id=int(driver.id),
        status=settlement_status,
        driver_share_model=driver_share_model,
        driver_share_value=driver_share_value,
        expected_customer_total=float(order.total or 0.0),
        actual_collected_amount=actual_collected_amount,
        food_revenue_amount=float(order.subtotal or 0.0),
        delivery_revenue_amount=float(order.delivery_fee or 0.0),
        driver_due_amount=driver_due_amount,
        store_due_amount=store_due_amount,
        remitted_amount=0.0,
        remaining_store_due_amount=store_due_amount,
        variance_amount=variance_amount,
        variance_reason="delivery_collected_amount_mismatch" if abs(variance_amount) > 0.009 else None,
        recognized_at=now,
    )
    db.add(settlement)
    db.flush()

    reference_group = build_reference_group(event_key="delivery_completed", order_id=int(order.id))
    create_delivery_detailed_entries(
        db,
        order=order,
        settlement=settlement,
        created_by=actor_id,
        reference_group=reference_group,
        note_prefix=f"Delivery completed for order #{order.id}",
    )

    return {
        "payment_status": PaymentStatus.PAID.value,
        "paid_at": now,
        "paid_by": actor_id,
        "amount_received": actual_collected_amount,
        "change_amount": 0.0,
        "payment_method": "cash",
        "collected_by_channel": CollectionChannel.DRIVER.value,
        "collection_variance_amount": variance_amount,
        "collection_variance_reason": settlement.variance_reason,
        "accounting_recognized_at": now,
    }


__all__ = [
    "build_reference_group",
    "create_delivery_detailed_entries",
    "record_delivery_completion",
    "record_financial_entry",
    "resolve_driver_share",
    "reverse_delivery_detailed_entries",
]
