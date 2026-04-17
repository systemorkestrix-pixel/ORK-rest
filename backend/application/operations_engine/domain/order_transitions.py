from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    DeliveryAssignmentStatus,
    DriverStatus,
    OrderStatus,
    OrderType,
)
from app.models import DeliveryAssignment, DeliveryDriver, Order
from app.orchestration.service_bridge import (
    app_ensure_delivery_operational,
    app_ensure_kitchen_operational,
    get_operational_capabilities,
    app_mark_cash_paid,
    app_refresh_table_occupancy_state,
)
from app.repositories.orders_repository import update_order_status_if_current_matches
from application.operations_engine.domain.constants import ORDER_CANCELLATION_REASONS
from application.operations_engine.domain.helpers import (
    compose_reason_text as _compose_reason_text,
    get_order_or_404,
    normalize_optional_text as _normalize_optional_text,
    record_system_audit as _record_system_audit,
    record_transition as _record_transition,
    resolve_standard_reason as _resolve_standard_reason,
)
from application.operations_engine.domain.order_transition_rules import ensure_transition_allowed
from application.operations_engine.domain.workflow_profiles import (
    is_delivery_managed_profile,
    is_kitchen_managed_profile,
    resolve_operational_workflow_profile,
)


def transition_order(
    db: Session,
    *,
    order_id: int,
    target_status: OrderStatus,
    performed_by: int,
    amount_received: float | None = None,
    collect_payment: bool = True,
    reason_code: str | None = None,
    reason_note: str | None = None,
) -> Order:
    order = get_order_or_404(db, order_id)
    capabilities = get_operational_capabilities(db)
    workflow_profile = resolve_operational_workflow_profile(
        activation_stage_id=str(capabilities.get("activation_stage_id") or "base"),
        order_type=order.type,
    )
    ensure_transition_allowed(
        current_status=order.status,
        target_status=target_status,
        order_type=order.type,
        workflow_profile=workflow_profile,
    )
    if target_status in (OrderStatus.IN_PREPARATION, OrderStatus.READY) and is_kitchen_managed_profile(workflow_profile):
        app_ensure_kitchen_operational(db)
    if target_status in (OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERY_FAILED) and is_delivery_managed_profile(workflow_profile):
        app_ensure_delivery_operational(db)

    update_values: dict[str, object] = {"status": target_status.value}
    cancellation_reason_text: str | None = None

    if target_status == OrderStatus.CANCELED:
        reason_label = _resolve_standard_reason(
            reason_code=reason_code,
            reasons_map=ORDER_CANCELLATION_REASONS,
            error_detail="سبب إلغاء الطلب مطلوب ويجب أن يكون ضمن الأسباب المعتمدة.",
        )
        cancellation_reason_text = _compose_reason_text(reason_label, reason_note)
        current_notes = _normalize_optional_text(order.notes)
        reason_line = f"سبب الإلغاء: {cancellation_reason_text}"
        update_values["notes"] = f"{current_notes}\n{reason_line}" if current_notes else reason_line
        if order.type == OrderType.DELIVERY.value:
            update_values["delivery_team_notified_at"] = None
            update_values["delivery_team_notified_by"] = None
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
            ).scalar_one_or_none()
            if active_assignment is not None:
                active_assignment.status = DeliveryAssignmentStatus.FAILED.value
                active_assignment.delivered_at = datetime.now(UTC)
                driver = db.execute(
                    select(DeliveryDriver).where(DeliveryDriver.id == active_assignment.driver_id)
                ).scalar_one_or_none()
                if driver is not None:
                    driver.status = DriverStatus.AVAILABLE.value if driver.active else DriverStatus.INACTIVE.value
    elif reason_code is not None or reason_note is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="سبب الانتقال يُستخدم فقط عند إلغاء الطلب.",
        )
    if target_status != OrderStatus.DELIVERED and amount_received is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="المبلغ المستلم يُستخدم فقط عند تسليم الطلب.",
        )
    if target_status != OrderStatus.DELIVERED and collect_payment is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="خيار التحصيل مرتبط فقط بعملية تسليم الطلب.",
        )

    if target_status == OrderStatus.DELIVERED:
        if not collect_payment and amount_received is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكن إدخال مبلغ مستلم عند تعطيل التحصيل أثناء التسليم.",
            )
        if order.type == OrderType.DINE_IN.value:
            # Dine-in orders are paid at table-session settlement, not per-order delivery.
            pass
        elif collect_payment:
            update_values.update(app_mark_cash_paid(db, order, amount_received, performed_by))
    # Delivery team notification is handled by Delivery Engine event handlers.

    updated_rows = update_order_status_if_current_matches(
        db,
        order_id=int(order.id),
        current_status=order.status,
        values=update_values,
    )
    if updated_rows != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="حدث تعارض أثناء تحديث حالة الطلب، يرجى إعادة المحاولة.",
        )

    _record_transition(
        db,
        order_id=order.id,
        from_status=order.status,
        to_status=target_status.value,
        user_id=performed_by,
    )
    if target_status == OrderStatus.CANCELED and cancellation_reason_text is not None:
        _record_system_audit(
            db,
            module="orders",
            action="cancel_order",
            entity_type="order",
            entity_id=order.id,
            user_id=performed_by,
            description=f"إلغاء الطلب #{order.id} | السبب: {cancellation_reason_text}",
        )
    if order.type == OrderType.DINE_IN.value and order.table_id is not None:
        app_refresh_table_occupancy_state(db, table_id=order.table_id)

    return get_order_or_404(db, order_id)
