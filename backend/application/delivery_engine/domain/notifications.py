from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import DeliveryAssignmentStatus, OrderStatus, OrderType
from app.models import DeliveryAssignment, Order
from app.orchestration.service_bridge import app_ensure_delivery_operational
from application.operations_engine.domain.helpers import get_order_or_404


def notify_delivery_team(
    db: Session,
    *,
    order_id: int,
    actor_id: int,
) -> Order:
    app_ensure_delivery_operational(db)
    order = get_order_or_404(db, order_id)
    if order.type != OrderType.DELIVERY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الطلب ليس من نوع التوصيل.",
        )
    if order.status not in (OrderStatus.IN_PREPARATION.value, OrderStatus.READY.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يمكن إشعار فريق التوصيل إلا عندما يكون الطلب قيد التحضير أو جاهز.",
        )

    active_assignment = (
        db.execute(
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
        )
        .scalar_one_or_none()
    )

    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تم إشعار فريق التوصيل بالفعل لهذا الطلب.",
        )

    order.delivery_team_notified_at = datetime.now(UTC)
    order.delivery_team_notified_by = actor_id

    return get_order_or_404(db, order_id)
