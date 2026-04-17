"""
Event Handler: DRIVER_DEPARTED
"""
import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.enums import OrderStatus
from app.models import Order
from app.schemas import OrderTransitionInput
from app.tx import transaction_scope
from application.operations_engine.use_cases import transition_order as transition_order_usecase
from core.events.event_bus import DomainEvent
from infrastructure.repositories import OrdersRepository

logger = logging.getLogger(__name__)


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
        if order.status == OrderStatus.OUT_FOR_DELIVERY.value:
            return
        transition_order_usecase.execute(
            data=transition_order_usecase.Input(
                actor_id=int(actor_id),
                order_id=int(order_id),
                payload=OrderTransitionInput(
                    target_status=OrderStatus.OUT_FOR_DELIVERY,
                    amount_received=None,
                    collect_payment=True,
                    reason_code=None,
                    reason_note=None,
                ),
            ),
            repo=OrdersRepository(db),
            transaction_scope=lambda: transaction_scope(db),
        )
    except Exception:
        logger.exception("Failed to handle DRIVER_DEPARTED for order_id=%s", order_id)
    finally:
        db.close()
