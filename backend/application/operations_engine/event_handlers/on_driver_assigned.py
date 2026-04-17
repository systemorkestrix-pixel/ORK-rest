"""
Event Handler: DRIVER_ASSIGNED
"""
import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Order
from app.tx import transaction_scope
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    order_id = event.payload.get("order_id")
    if not order_id:
        return

    db = SessionLocal()
    try:
        with transaction_scope(db):
            order = db.execute(select(Order).where(Order.id == int(order_id))).scalar_one_or_none()
            if order is None:
                return
            if order.delivery_team_notified_at is None:
                return
            # Reserve order by clearing delivery team notification flag.
            order.delivery_team_notified_at = None
            order.delivery_team_notified_by = None
    except Exception:
        logger.exception("Failed to handle DRIVER_ASSIGNED for order_id=%s", order_id)
    finally:
        db.close()
