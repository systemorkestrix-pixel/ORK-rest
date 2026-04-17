"""
Event Handler: ORDER_PREPARATION_STARTED
"""
import logging

from sqlalchemy import func, select

from app.database import SessionLocal
from app.enums import DriverStatus, OrderType
from app.models import DeliveryDriver, Order
from app.tx import transaction_scope
from application.delivery_engine.use_cases import notify_delivery_team as notify_delivery_team_usecase
from application.operations_engine.use_cases import get_delivery_policies as get_delivery_policies_usecase
from core.events.event_bus import DomainEvent
from infrastructure.repositories import DeliveryRepository, OperationsRepository

logger = logging.getLogger(__name__)

def _count_active_delivery_users(db) -> int:
    return int(
        db.execute(
            select(func.count(DeliveryDriver.id))
            .select_from(DeliveryDriver)
            .where(
                DeliveryDriver.active.is_(True),
                DeliveryDriver.status != DriverStatus.INACTIVE.value,
            )
        ).scalar_one()
        or 0
    )


def handle(event: DomainEvent) -> None:
    order_id = event.payload.get("order_id")
    actor_id = event.actor_id
    if not order_id or actor_id is None:
        return

    db = SessionLocal()
    try:
        order = db.execute(select(Order).where(Order.id == int(order_id))).scalar_one_or_none()
        if order is None:
            return
        if order.type != OrderType.DELIVERY.value:
            return
        if order.delivery_team_notified_at is not None:
            return
        policy = get_delivery_policies_usecase.execute(
            data=get_delivery_policies_usecase.Input(),
            repo=OperationsRepository(db),
            transaction_scope=lambda: transaction_scope(db),
        ).result
        if not bool(policy.auto_notify_team):
            return
        if _count_active_delivery_users(db) <= 0:
            return
        notify_delivery_team_usecase.execute(
            data=notify_delivery_team_usecase.Input(
                actor_id=int(actor_id),
                order_id=int(order_id),
            ),
            repo=DeliveryRepository(db),
            transaction_scope=lambda: transaction_scope(db),
        )
    except Exception:
        logger.exception("Failed to handle ORDER_PREPARATION_STARTED for order_id=%s", order_id)
    finally:
        db.close()
