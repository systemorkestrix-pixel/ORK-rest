from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import (
    CashboxMovementDirection,
    CashboxMovementType,
    CashChannel,
    DeliverySettlementStatus,
    DriverShareModel,
    OrderStatus,
    OrderType,
)
from app.models import CashboxMovement, DeliverySettlement, Order
from application.financial_engine.domain.helpers import (
    get_order_or_404,
    normalize_optional_text,
    record_system_audit,
)
from app.tx import transaction_scope

def _sum_settlement_cashbox_movements(db: Session, *, settlement_id: int, movement_type: str) -> float:
    value = db.execute(
        select(func.coalesce(func.sum(CashboxMovement.amount), 0.0)).where(
            CashboxMovement.delivery_settlement_id == settlement_id,
            CashboxMovement.type == movement_type,
        )
    ).scalar_one()
    return float(value or 0.0)


def _refresh_delivery_settlement_status(
    db: Session,
    *,
    settlement: DeliverySettlement,
    actor_id: int | None = None,
) -> DeliverySettlement:
    if settlement.status == DeliverySettlementStatus.REVERSED.value:
        return settlement

    remitted_total = _sum_settlement_cashbox_movements(
        db,
        settlement_id=int(settlement.id),
        movement_type=CashboxMovementType.DRIVER_REMITTANCE.value,
    )
    settlement.remitted_amount = round(remitted_total, 2)
    settlement.remaining_store_due_amount = round(float(settlement.store_due_amount or 0.0) - remitted_total, 2)

    if abs(settlement.remaining_store_due_amount) <= 0.009:
        settlement.status = DeliverySettlementStatus.SETTLED.value
        settlement.settled_at = datetime.now(UTC)
        if actor_id is not None:
            settlement.settled_by = actor_id
    elif remitted_total > 0.0:
        settlement.status = DeliverySettlementStatus.PARTIALLY_REMITTED.value
    elif abs(float(settlement.variance_amount or 0.0)) > 0.009:
        settlement.status = DeliverySettlementStatus.VARIANCE.value
    else:
        settlement.status = DeliverySettlementStatus.PENDING.value

    return settlement


def record_driver_remittance(
    db: Session,
    *,
    settlement_id: int,
    amount: float,
    performed_by: int,
    cash_channel: str = CashChannel.CASH_DRAWER.value,
    note: str | None = None,
) -> DeliverySettlement:
    safe_amount = round(float(amount), 2)
    if safe_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مبلغ التوريد يجب أن يكون أكبر من صفر.")

    with transaction_scope(db):
        settlement = db.execute(
            select(DeliverySettlement).where(DeliverySettlement.id == settlement_id)
        ).scalar_one_or_none()
        if settlement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تسوية التوصيل غير موجودة.")
        if settlement.status == DeliverySettlementStatus.REVERSED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن توريد تسوية ملغاة.")

        current_remaining = round(float(settlement.remaining_store_due_amount or settlement.store_due_amount or 0.0), 2)
        if current_remaining >= 0 and safe_amount > current_remaining + 0.01:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مبلغ التوريد أكبر من المستحق للمحل.")

        db.add(
            CashboxMovement(
                delivery_settlement_id=int(settlement.id),
                order_id=int(settlement.order_id),
                type=CashboxMovementType.DRIVER_REMITTANCE.value,
                direction=CashboxMovementDirection.IN.value,
                amount=safe_amount,
                cash_channel=cash_channel,
                performed_by=performed_by,
                created_at=datetime.now(UTC),
                note=normalize_optional_text(note),
            )
        )
        db.flush()
        settlement = _refresh_delivery_settlement_status(db, settlement=settlement, actor_id=performed_by)
        record_system_audit(
            db,
            module="financial",
            action="driver_remittance",
            entity_type="delivery_settlement",
            entity_id=settlement.id,
            user_id=performed_by,
            description=f"توريد مندوب للتسوية #{settlement.id} بمبلغ {safe_amount:.2f} د.ج.",
        )

    return settlement


def record_driver_payout(
    db: Session,
    *,
    settlement_id: int,
    amount: float,
    performed_by: int,
    cash_channel: str = CashChannel.CASH_DRAWER.value,
    note: str | None = None,
) -> DeliverySettlement:
    safe_amount = round(float(amount), 2)
    if safe_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مبلغ دفع المندوب يجب أن يكون أكبر من صفر.")

    with transaction_scope(db):
        settlement = db.execute(
            select(DeliverySettlement).where(DeliverySettlement.id == settlement_id)
        ).scalar_one_or_none()
        if settlement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تسوية التوصيل غير موجودة.")
        if settlement.status == DeliverySettlementStatus.REVERSED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن دفع مستحق تسوية ملغاة.")

        if settlement.driver_share_model == DriverShareModel.FULL_DELIVERY_FEE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يلزم دفع منفصل للمندوب في هذا النموذج.",
            )

        payout_total = _sum_settlement_cashbox_movements(
            db,
            settlement_id=int(settlement.id),
            movement_type=CashboxMovementType.DRIVER_PAYOUT.value,
        )
        if payout_total + safe_amount > float(settlement.driver_due_amount or 0.0) + 0.01:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مبلغ الدفع يتجاوز مستحق المندوب.")

        db.add(
            CashboxMovement(
                delivery_settlement_id=int(settlement.id),
                order_id=int(settlement.order_id),
                type=CashboxMovementType.DRIVER_PAYOUT.value,
                direction=CashboxMovementDirection.OUT.value,
                amount=safe_amount,
                cash_channel=cash_channel,
                performed_by=performed_by,
                created_at=datetime.now(UTC),
                note=normalize_optional_text(note),
            )
        )
        db.flush()
        settlement = _refresh_delivery_settlement_status(db, settlement=settlement, actor_id=performed_by)
        record_system_audit(
            db,
            module="financial",
            action="driver_payout",
            entity_type="delivery_settlement",
            entity_id=settlement.id,
            user_id=performed_by,
            description=f"دفع مستحق مندوب للتسوية #{settlement.id} بمبلغ {safe_amount:.2f} د.ج.",
        )

    return settlement


def settle_delivery_order(
    db: Session,
    *,
    order_id: int,
    performed_by: int,
    cash_channel: str = CashChannel.CASH_DRAWER.value,
) -> DeliverySettlement:
    with transaction_scope(db):
        order = get_order_or_404(db, order_id)
        if order.type != OrderType.DELIVERY.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="إجراء التسوية مخصص لطلبات التوصيل فقط.")
        if order.status != OrderStatus.DELIVERED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن تسوية طلب لم يتم تسليمه بعد.")

        settlement = db.execute(
            select(DeliverySettlement).where(DeliverySettlement.order_id == order_id)
        ).scalar_one_or_none()
        if settlement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تسوية التوصيل غير موجودة لهذا الطلب.")
        if settlement.status == DeliverySettlementStatus.REVERSED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا يمكن تسوية طلب ملغى.")

        settlement = _refresh_delivery_settlement_status(db, settlement=settlement, actor_id=performed_by)
        remaining_amount = round(float(settlement.remaining_store_due_amount or 0.0), 2)
        if remaining_amount <= 0.009:
            db.flush()
            return settlement

    return record_driver_remittance(
        db,
        settlement_id=int(settlement.id),
        amount=remaining_amount,
        performed_by=performed_by,
        cash_channel=cash_channel,
        note=f"تسوية طلب التوصيل #{order_id} بتوريد مستحق المطعم.",
    )
