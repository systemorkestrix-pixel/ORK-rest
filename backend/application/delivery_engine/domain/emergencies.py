from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.enums import DeliveryAssignmentStatus, DriverStatus, OrderStatus, OrderType
from app.models import DeliveryAssignment, DeliveryDriver, Order
from application.operations_engine.domain import get_operational_capabilities
from application.operations_engine.domain.helpers import (
    compose_reason_text,
    get_order_or_404,
    normalize_optional_text,
    record_system_audit,
    record_transition,
    resolve_standard_reason,
)

EMERGENCY_DELIVERY_FAIL_REASONS: dict[str, str] = {
    "delivery_service_disabled": "خدمة التوصيل متوقفة",
    "no_driver_available": "لا يوجد سائق متاح",
    "address_issue": "مشكلة في العنوان",
    "customer_unreachable": "تعذر التواصل مع العميل",
    "operational_emergency": "طارئ تشغيلي",
}

TERMINAL_ORDER_STATUSES = (
    OrderStatus.DELIVERED.value,
    OrderStatus.CANCELED.value,
    OrderStatus.DELIVERY_FAILED.value,
)


def emergency_fail_delivery_order(
    db: Session,
    *,
    order_id: int,
    performed_by: int,
    reason_code: str,
    reason_note: str | None = None,
) -> Order:
    capabilities = get_operational_capabilities(db)
    if capabilities["delivery_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تسجيل فشل طارئ للتوصيل ما دامت خدمة التوصيل مفعّلة.",
        )

    order = get_order_or_404(db, order_id)
    if order.type != OrderType.DELIVERY.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الطلب ليس طلب توصيل.")
    if order.status in TERMINAL_ORDER_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الطلب مغلق بالفعل.")
    if order.status not in (
        OrderStatus.IN_PREPARATION.value,
        OrderStatus.READY.value,
        OrderStatus.OUT_FOR_DELIVERY.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن تسجيل الفشل الطارئ إلا أثناء التحضير أو الجاهزية أو أثناء التوصيل.",
        )

    reason_label = resolve_standard_reason(
        reason_code=reason_code,
        reasons_map=EMERGENCY_DELIVERY_FAIL_REASONS,
        error_detail="سبب فشل التوصيل غير معروف أو غير مدعوم.",
    )
    emergency_reason_text = compose_reason_text(reason_label, reason_note)
    current_notes = normalize_optional_text(order.notes)

    active_assignment = db.execute(
        select(DeliveryAssignment)
        .where(
            DeliveryAssignment.order_id == order_id,
            DeliveryAssignment.status.in_(
                [
                    DeliveryAssignmentStatus.ASSIGNED.value,
                    DeliveryAssignmentStatus.DEPARTED.value,
                ]
            ),
        )
        .order_by(DeliveryAssignment.id.desc())
    ).scalar_one_or_none()

    if active_assignment is not None:
        active_assignment.status = DeliveryAssignmentStatus.FAILED.value
        active_assignment.delivered_at = datetime.now(UTC)
        driver = db.execute(
            select(DeliveryDriver).where(DeliveryDriver.id == active_assignment.driver_id)
        ).scalar_one_or_none()
        if driver is not None:
            driver.status = DriverStatus.AVAILABLE.value if driver.active else DriverStatus.INACTIVE.value

    result = db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == order.status)
        .values(
            status=OrderStatus.DELIVERY_FAILED.value,
            delivery_team_notified_at=None,
            delivery_team_notified_by=None,
            delivery_failure_resolution_status=None,
            delivery_failure_resolution_note=None,
            delivery_failure_resolved_at=None,
            delivery_failure_resolved_by=None,
            notes=(
                f"{current_notes}\nسبب فشل التوصيل الطارئ: {emergency_reason_text}"
                if current_notes
                else f"سبب فشل التوصيل الطارئ: {emergency_reason_text}"
            ),
        )
    )
    if result.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to update delivery failure status due to a concurrent change.",
        )

    record_transition(
        db,
        order_id=order.id,
        from_status=order.status,
        to_status=OrderStatus.DELIVERY_FAILED.value,
        user_id=performed_by,
    )
    record_system_audit(
        db,
        module="delivery",
        action="emergency_fail_order",
        entity_type="order",
        entity_id=order.id,
        user_id=performed_by,
        description=f"فشل توصيل طارئ للطلب #{order.id} | السبب: {emergency_reason_text}",
    )

    return get_order_or_404(db, order_id)
