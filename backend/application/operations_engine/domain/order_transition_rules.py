from __future__ import annotations

from fastapi import HTTPException, status

from app.enums import OrderStatus, OrderType
from app.lifecycle import can_transition
from application.operations_engine.domain.order_status_presentation import ORDER_STATUS_ARABIC_LABELS
from application.operations_engine.domain.workflow_profiles import OperationalWorkflowProfile


def ensure_transition_allowed(
    *,
    current_status: str,
    target_status: OrderStatus,
    order_type: str,
    workflow_profile: OperationalWorkflowProfile | str,
) -> None:
    try:
        current = OrderStatus(current_status)
        order_type_value = OrderType(order_type)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حالة الطلب غير صالحة.") from error

    if not can_transition(current, target_status, order_type_value, workflow_profile):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"لا يمكن الانتقال من "
                f"{ORDER_STATUS_ARABIC_LABELS.get(current, current.value)} "
                f"إلى {ORDER_STATUS_ARABIC_LABELS.get(target_status, target_status.value)}."
            ),
        )
