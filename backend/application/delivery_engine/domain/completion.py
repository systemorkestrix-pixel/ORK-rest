from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.enums import DeliveryAssignmentStatus, DriverStatus, OrderStatus
from app.models import DeliveryAssignment, DeliveryDriver, Order
from app.orchestration.service_bridge import (
    app_ensure_delivery_operational,
    app_record_delivery_completion as _record_delivery_completion,
)
from application.delivery_engine.domain.helpers import get_delivery_driver_for_user
from application.operations_engine.domain.helpers import get_order_or_404
from application.operations_engine.domain.helpers import record_transition as _record_transition
from application.operations_engine.domain.order_transition_rules import ensure_transition_allowed


DeliveryCompletionRecorder = Callable[..., dict[str, object]]


def finalize_delivery_completion(
    *,
    order: Order,
    assignment: DeliveryAssignment,
    driver: DeliveryDriver,
    success: bool,
    amount_received: float | None,
    actor_id: int,
    record_completion: DeliveryCompletionRecorder,
) -> tuple[OrderStatus, dict[str, object]]:
    target = OrderStatus.DELIVERED if success else OrderStatus.DELIVERY_FAILED
    update_values: dict[str, object] = {"status": target.value}
    now = datetime.now(UTC)

    if target == OrderStatus.DELIVERED:
        assignment.status = DeliveryAssignmentStatus.DELIVERED.value
        assignment.delivered_at = now
        update_values.update(
            record_completion(
                order=order,
                assignment=assignment,
                driver=driver,
                amount_received=amount_received,
                actor_id=actor_id,
            )
        )
    else:
        assignment.status = DeliveryAssignmentStatus.FAILED.value
        assignment.delivered_at = now
        update_values.update(
            {
                "delivery_failure_resolution_status": None,
                "delivery_failure_resolution_note": None,
                "delivery_failure_resolved_at": None,
                "delivery_failure_resolved_by": None,
            }
        )

    driver.status = DriverStatus.AVAILABLE.value if driver.active else DriverStatus.INACTIVE.value
    return target, update_values


def _get_driver_or_404(db: Session, *, driver_id: int) -> DeliveryDriver:
    driver = db.execute(select(DeliveryDriver).where(DeliveryDriver.id == driver_id)).scalar_one_or_none()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
    return driver


def _complete_delivery_for_driver(
    db: Session,
    *,
    order_id: int,
    driver: DeliveryDriver,
    actor_id: int,
    success: bool,
    amount_received: float | None = None,
) -> Order:
    app_ensure_delivery_operational(db)
    order = get_order_or_404(db, order_id)
    assignment = db.execute(
        select(DeliveryAssignment)
        .where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.driver_id == driver.id,
            DeliveryAssignment.status == DeliveryAssignmentStatus.DEPARTED.value,
        )
        .order_by(DeliveryAssignment.id.desc())
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="لا يمكن إنهاء طلب غير تابع لك أو خارج مسار التوصيل.")

    target_status = OrderStatus.DELIVERED if success else OrderStatus.DELIVERY_FAILED
    ensure_transition_allowed(
        current_status=order.status,
        target_status=target_status,
        order_type=order.type,
    )

    target, update_values = finalize_delivery_completion(
        order=order,
        assignment=assignment,
        driver=driver,
        success=success,
        amount_received=amount_received,
        actor_id=actor_id,
        record_completion=lambda **kwargs: _record_delivery_completion(db, **kwargs),
    )

    result = db.execute(
        update(Order)
        .where(Order.id == order_id, Order.status == order.status)
        .values(**update_values)
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تعذر تحديث حالة الطلب.")

    _record_transition(
        db,
        order_id=order_id,
        from_status=order.status,
        to_status=target.value,
        user_id=actor_id,
    )
    return get_order_or_404(db, order_id)


def complete_delivery(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
    success: bool,
    amount_received: float | None = None,
) -> Order:
    driver = get_delivery_driver_for_user(db, user_id=actor_id, require_active=False)
    return _complete_delivery_for_driver(
        db,
        order_id=order_id,
        driver=driver,
        actor_id=actor_id,
        success=success,
        amount_received=amount_received,
    )


def complete_delivery_for_driver(
    db: Session,
    *,
    order_id: int,
    driver_id: int,
    actor_id: int,
    success: bool,
    amount_received: float | None = None,
) -> Order:
    driver = _get_driver_or_404(db, driver_id=driver_id)
    return _complete_delivery_for_driver(
        db,
        order_id=order_id,
        driver=driver,
        actor_id=actor_id,
        success=success,
        amount_received=amount_received,
    )
