from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.enums import (
    DeliveryAssignmentStatus,
    DeliveryDispatchScope,
    DeliveryDispatchStatus,
    DriverStatus,
    OrderStatus,
    OrderType,
)
from app.models import DeliveryAssignment, DeliveryDispatch, DeliveryDriver, Order
from app.orchestration.service_bridge import app_ensure_delivery_operational
from application.delivery_engine.domain.helpers import get_delivery_driver_for_user
from application.operations_engine.domain.helpers import get_order_or_404, record_transition
from application.operations_engine.domain.order_transition_rules import ensure_transition_allowed


def assign_delivery_order(
    db: Session,
    *,
    order: Order,
    driver: DeliveryDriver,
) -> DeliveryAssignment:
    if order.type != OrderType.DELIVERY.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الطلب ليس من نوع التوصيل.")
    if order.status not in (OrderStatus.IN_PREPARATION.value, OrderStatus.READY.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="التقاط الطلب متاح فقط أثناء التحضير أو الجاهزية.",
        )
    if order.delivery_team_notified_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم يتم تبليغ فريق التوصيل لهذا الطلب.",
        )

    active_assignment = db.execute(
        select(DeliveryAssignment)
        .where(
            DeliveryAssignment.order_id == int(order.id),
            DeliveryAssignment.status.in_(
                [
                    DeliveryAssignmentStatus.ASSIGNED.value,
                    DeliveryAssignmentStatus.DEPARTED.value,
                ]
            ),
        )
        .order_by(DeliveryAssignment.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if active_assignment:
        if active_assignment.driver_id == driver.id:
            return active_assignment
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تم التقاط الطلب بواسطة سائق آخر.")

    if driver.status == DriverStatus.BUSY.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="سائق التوصيل مشغول بطلب آخر.")

    reserved = db.execute(
        update(Order)
        .where(
            Order.id == int(order.id),
            Order.status.in_([OrderStatus.IN_PREPARATION.value, OrderStatus.READY.value]),
            Order.delivery_team_notified_at.is_not(None),
        )
        .values(delivery_team_notified_at=None)
    )
    if reserved.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تم التقاط الطلب بواسطة سائق آخر.")

    assignment = DeliveryAssignment(
        order_id=int(order.id),
        driver_id=int(driver.id),
        status=DeliveryAssignmentStatus.ASSIGNED.value,
    )
    db.add(assignment)
    db.flush()

    driver.status = DriverStatus.BUSY.value
    return assignment


def _get_driver_or_404(db: Session, *, driver_id: int, require_active: bool) -> DeliveryDriver:
    driver = db.execute(select(DeliveryDriver).where(DeliveryDriver.id == driver_id)).scalar_one_or_none()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سائق التوصيل غير موجود.")
    if require_active and (not driver.active or driver.status == DriverStatus.INACTIVE.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="سائق التوصيل غير متاح حاليًا.")
    return driver


def _claim_delivery_order_for_driver(
    db: Session,
    *,
    order_id: int,
    driver: DeliveryDriver,
    actor_id: int,
) -> DeliveryAssignment:
    del actor_id
    app_ensure_delivery_operational(db)
    order = get_order_or_404(db, order_id)
    dispatch = db.execute(
        select(DeliveryDispatch)
        .where(DeliveryDispatch.order_id == order_id)
        .order_by(DeliveryDispatch.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if dispatch is not None:
        if dispatch.status != DeliveryDispatchStatus.OFFERED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="هذا الطلب يحتاج إرسال عرض جديد قبل الالتقاط.",
            )
        matches_driver = (
            dispatch.dispatch_scope == DeliveryDispatchScope.DRIVER.value and dispatch.driver_id == driver.id
        )
        matches_provider = (
            dispatch.dispatch_scope == DeliveryDispatchScope.PROVIDER.value
            and dispatch.provider_id is not None
            and driver.provider_id == dispatch.provider_id
        )
        if not (matches_driver or matches_provider):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="هذا العرض غير موجه إلى عنصر التوصيل الحالي.",
            )
        dispatch.status = DeliveryDispatchStatus.ACCEPTED.value
        dispatch.responded_at = datetime.now(UTC)
        if dispatch.driver_id is None:
            dispatch.driver_id = int(driver.id)
    return assign_delivery_order(db, order=order, driver=driver)


def claim_delivery_order(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
) -> DeliveryAssignment:
    driver = get_delivery_driver_for_user(db, user_id=actor_id, require_active=True)
    return _claim_delivery_order_for_driver(
        db,
        order_id=order_id,
        driver=driver,
        actor_id=actor_id,
    )


def claim_delivery_order_for_driver(
    db: Session,
    *,
    order_id: int,
    driver_id: int,
    actor_id: int,
) -> DeliveryAssignment:
    driver = _get_driver_or_404(db, driver_id=driver_id, require_active=True)
    return _claim_delivery_order_for_driver(
        db,
        order_id=order_id,
        driver=driver,
        actor_id=actor_id,
    )


def _start_delivery_for_driver(
    db: Session,
    *,
    order_id: int,
    driver: DeliveryDriver,
    actor_id: int,
) -> Order:
    app_ensure_delivery_operational(db)
    order = get_order_or_404(db, order_id)
    if order.type != OrderType.DELIVERY.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الطلب ليس من نوع التوصيل.")

    assignment = db.execute(
        select(DeliveryAssignment)
        .where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.driver_id == driver.id,
            DeliveryAssignment.status == DeliveryAssignmentStatus.ASSIGNED.value,
        )
        .order_by(DeliveryAssignment.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا الطلب غير مُسند إلى هذا السائق.")

    ensure_transition_allowed(
        current_status=order.status,
        target_status=OrderStatus.OUT_FOR_DELIVERY,
        order_type=order.type,
    )
    result = db.execute(
        update(Order)
        .where(Order.id == order_id, Order.status == order.status)
        .values(status=OrderStatus.OUT_FOR_DELIVERY.value)
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="تعذر تحديث حالة الطلب.")

    assignment.status = DeliveryAssignmentStatus.DEPARTED.value
    assignment.departed_at = datetime.now(UTC)
    driver.status = DriverStatus.BUSY.value

    record_transition(
        db,
        order_id=order_id,
        from_status=order.status,
        to_status=OrderStatus.OUT_FOR_DELIVERY.value,
        user_id=actor_id,
    )

    return get_order_or_404(db, order_id)


def start_delivery(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
) -> Order:
    driver = get_delivery_driver_for_user(db, user_id=actor_id, require_active=True)
    return _start_delivery_for_driver(
        db,
        order_id=order_id,
        driver=driver,
        actor_id=actor_id,
    )


def start_delivery_for_driver(
    db: Session,
    *,
    order_id: int,
    driver_id: int,
    actor_id: int,
) -> Order:
    driver = _get_driver_or_404(db, driver_id=driver_id, require_active=True)
    return _start_delivery_for_driver(
        db,
        order_id=order_id,
        driver=driver,
        actor_id=actor_id,
    )
