from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import CollectionChannel, DeliverySettlementStatus, OrderStatus, OrderType, PaymentStatus
from app.models import DeliveryAssignment, DeliveryDriver, DeliverySettlement, Order, SystemSetting
from app.tx import transaction_scope
from application.financial_engine.domain.delivery_accounting import (
    create_delivery_detailed_entries,
    resolve_driver_share,
    reverse_delivery_detailed_entries,
)
from application.financial_engine.domain.helpers import record_system_audit


LEGACY_BACKFILL_NOTE_PREFIX = "Legacy backfill"
LEGACY_ASSUMED_AMOUNT_REASON = "legacy_assumed_total"
LEGACY_BACKFILL_LAST_RUN_AT_KEY = "delivery_accounting_backfill_last_run_at"
LEGACY_BACKFILL_LAST_RUN_BY_KEY = "delivery_accounting_backfill_last_run_by"
LEGACY_BACKFILL_CUTOVER_AT_KEY = "delivery_accounting_cutover_completed_at"


def _latest_delivery_assignment(db: Session, *, order_id: int) -> DeliveryAssignment | None:
    return (
        db.execute(
            select(DeliveryAssignment)
            .where(DeliveryAssignment.order_id == order_id)
            .order_by(DeliveryAssignment.delivered_at.desc().nullslast(), DeliveryAssignment.id.desc())
        )
        .scalars()
        .first()
    )


def _read_system_setting(db: Session, *, key: str) -> str | None:
    row = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    return None if row is None else str(row.value)


def _write_system_setting(db: Session, *, key: str, value: str, actor_id: int) -> None:
    row = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalar_one_or_none()
    if row is None:
        db.add(SystemSetting(key=key, value=value, updated_by=actor_id))
        return
    row.value = value
    row.updated_at = datetime.now(UTC)
    row.updated_by = actor_id


def _parse_setting_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _legacy_delivery_orders_without_settlement(db: Session, *, limit: int | None = None) -> list[Order]:
    stmt = (
        select(Order)
        .outerjoin(DeliverySettlement, DeliverySettlement.order_id == Order.id)
        .where(
            Order.type == OrderType.DELIVERY.value,
            Order.status == OrderStatus.DELIVERED.value,
            Order.payment_status.in_((PaymentStatus.PAID.value, PaymentStatus.REFUNDED.value)),
            DeliverySettlement.id.is_(None),
        )
        .order_by(Order.id.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return db.execute(stmt).scalars().all()


def get_delivery_accounting_migration_status(db: Session) -> dict[str, object]:
    candidate_orders = _legacy_delivery_orders_without_settlement(db)
    blocked_missing_assignment_order_ids: list[int] = []
    blocked_missing_driver_order_ids: list[int] = []
    pending_order_ids: list[int] = []

    for order in candidate_orders:
        assignment = _latest_delivery_assignment(db, order_id=int(order.id))
        if assignment is None:
            blocked_missing_assignment_order_ids.append(int(order.id))
            continue
        driver = db.execute(select(DeliveryDriver).where(DeliveryDriver.id == int(assignment.driver_id))).scalar_one_or_none()
        if driver is None:
            blocked_missing_driver_order_ids.append(int(order.id))
            continue
        pending_order_ids.append(int(order.id))

    backfilled_orders = int(
        db.execute(
            select(func.count(DeliverySettlement.id)).where(DeliverySettlement.note.ilike(f"{LEGACY_BACKFILL_NOTE_PREFIX}%"))
        ).scalar_one()
        or 0
    )
    assumed_amount_received_orders = int(
        db.execute(
            select(func.count(DeliverySettlement.id)).where(
                DeliverySettlement.variance_reason == LEGACY_ASSUMED_AMOUNT_REASON
            )
        ).scalar_one()
        or 0
    )
    last_backfill_at = _parse_setting_datetime(_read_system_setting(db, key=LEGACY_BACKFILL_LAST_RUN_AT_KEY))
    last_backfill_by_raw = _read_system_setting(db, key=LEGACY_BACKFILL_LAST_RUN_BY_KEY)
    cutover_completed_at = _parse_setting_datetime(_read_system_setting(db, key=LEGACY_BACKFILL_CUTOVER_AT_KEY))

    return {
        "legacy_candidates": len(candidate_orders),
        "pending_migratable": len(pending_order_ids),
        "blocked_missing_assignment": len(blocked_missing_assignment_order_ids),
        "blocked_missing_driver": len(blocked_missing_driver_order_ids),
        "backfilled_orders": backfilled_orders,
        "assumed_amount_received_orders": assumed_amount_received_orders,
        "cutover_ready": len(candidate_orders) == 0,
        "cutover_completed_at": cutover_completed_at,
        "last_backfill_at": last_backfill_at,
        "last_backfill_by": int(last_backfill_by_raw) if last_backfill_by_raw and last_backfill_by_raw.isdigit() else None,
        "pending_order_ids": pending_order_ids[:10],
        "blocked_missing_assignment_order_ids": blocked_missing_assignment_order_ids[:10],
        "blocked_missing_driver_order_ids": blocked_missing_driver_order_ids[:10],
    }


def run_delivery_accounting_backfill(
    db: Session,
    *,
    actor_id: int,
    limit: int = 100,
    dry_run: bool = False,
) -> dict[str, object]:
    safe_limit = max(1, min(int(limit), 500))
    migrated_order_ids: list[int] = []
    skipped_missing_assignment_order_ids: list[int] = []
    skipped_missing_driver_order_ids: list[int] = []
    assumed_amount_received_orders = 0
    processed_orders = 0

    with transaction_scope(db):
        orders = _legacy_delivery_orders_without_settlement(db, limit=safe_limit)
        processed_orders = len(orders)
        for order in orders:
            assignment = _latest_delivery_assignment(db, order_id=int(order.id))
            if assignment is None:
                skipped_missing_assignment_order_ids.append(int(order.id))
                continue

            driver = db.execute(
                select(DeliveryDriver).where(DeliveryDriver.id == int(assignment.driver_id))
            ).scalar_one_or_none()
            if driver is None:
                skipped_missing_driver_order_ids.append(int(order.id))
                continue

            actual_collected_amount = float(order.amount_received if order.amount_received is not None else (order.total or 0.0))
            if actual_collected_amount <= 0:
                actual_collected_amount = float(order.total or 0.0)

            recognized_at = (
                order.accounting_recognized_at
                or order.paid_at
                or assignment.delivered_at
                or order.created_at
                or datetime.now(UTC)
            )
            variance_amount = round(actual_collected_amount - float(order.total or 0.0), 2)
            driver_share_model, driver_share_value, driver_due_amount = resolve_driver_share(
                driver,
                delivery_fee=float(order.delivery_fee or 0.0),
            )
            store_due_amount = round(actual_collected_amount - driver_due_amount, 2)

            legacy_note_parts = [LEGACY_BACKFILL_NOTE_PREFIX]
            variance_reason = order.collection_variance_reason
            if order.amount_received is None:
                variance_reason = LEGACY_ASSUMED_AMOUNT_REASON
                assumed_amount_received_orders += 1
                legacy_note_parts.append("assumed_amount_received=order.total")
            if variance_amount != 0 and variance_reason is None:
                variance_reason = "legacy_variance_detected"
            if order.payment_status == PaymentStatus.REFUNDED.value:
                legacy_note_parts.append("refunded")

            if dry_run:
                migrated_order_ids.append(int(order.id))
                continue

            settlement = DeliverySettlement(
                order_id=int(order.id),
                assignment_id=int(assignment.id),
                driver_id=int(driver.id),
                status=(
                    DeliverySettlementStatus.VARIANCE.value
                    if abs(variance_amount) > 0.009
                    else DeliverySettlementStatus.PENDING.value
                ),
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
                variance_reason=variance_reason,
                recognized_at=recognized_at,
                note=" | ".join(legacy_note_parts),
            )
            db.add(settlement)
            db.flush()

            reference_group = f"legacy_backfill:order:{order.id}"
            create_delivery_detailed_entries(
                db,
                order=order,
                settlement=settlement,
                created_by=actor_id,
                reference_group=reference_group,
                note_prefix=f"{LEGACY_BACKFILL_NOTE_PREFIX} for order #{order.id}",
            )

            order.collected_by_channel = CollectionChannel.DRIVER.value
            order.collection_variance_amount = variance_amount
            order.collection_variance_reason = variance_reason
            order.accounting_recognized_at = recognized_at
            if order.amount_received is None:
                order.amount_received = actual_collected_amount

            if order.payment_status == PaymentStatus.REFUNDED.value:
                reverse_delivery_detailed_entries(
                    db,
                    order=order,
                    refunded_by=actor_id,
                    note=f"{LEGACY_BACKFILL_NOTE_PREFIX} refund sync",
                )
                settlement.note = f"{settlement.note or LEGACY_BACKFILL_NOTE_PREFIX} | refund_reversed"

            migrated_order_ids.append(int(order.id))

        _write_system_setting(
            db,
            key=LEGACY_BACKFILL_LAST_RUN_AT_KEY,
            value=datetime.now(UTC).isoformat(),
            actor_id=actor_id,
        )
        _write_system_setting(
            db,
            key=LEGACY_BACKFILL_LAST_RUN_BY_KEY,
            value=str(actor_id),
            actor_id=actor_id,
        )

        remaining_candidates = _legacy_delivery_orders_without_settlement(db)
        if not dry_run and len(remaining_candidates) == 0:
            _write_system_setting(
                db,
                key=LEGACY_BACKFILL_CUTOVER_AT_KEY,
                value=datetime.now(UTC).isoformat(),
                actor_id=actor_id,
            )

        record_system_audit(
            db,
            module="financial",
            action="delivery_accounting_backfill",
            entity_type="delivery_accounting",
            entity_id=None,
            user_id=actor_id,
            description=(
                f"Legacy delivery backfill run dry_run={str(dry_run).lower()} "
                f"processed={len(orders)} migrated={len(migrated_order_ids)} "
                f"missing_assignment={len(skipped_missing_assignment_order_ids)} "
                f"missing_driver={len(skipped_missing_driver_order_ids)}."
            ),
        )

    return {
        "processed_orders": processed_orders,
        "migrated_orders": len(migrated_order_ids),
        "blocked_missing_assignment": len(skipped_missing_assignment_order_ids),
        "blocked_missing_driver": len(skipped_missing_driver_order_ids),
        "assumed_amount_received_orders": assumed_amount_received_orders,
        "dry_run": dry_run,
        "migrated_order_ids": migrated_order_ids[:20],
        "skipped_missing_assignment_order_ids": skipped_missing_assignment_order_ids[:20],
        "skipped_missing_driver_order_ids": skipped_missing_driver_order_ids[:20],
        "status": get_delivery_accounting_migration_status(db),
    }


__all__ = [
    "get_delivery_accounting_migration_status",
    "run_delivery_accounting_backfill",
]
