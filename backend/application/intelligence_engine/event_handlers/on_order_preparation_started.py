"""
Event Handler: ORDER_PREPARATION_STARTED
"""
import logging

from application._shared.event_audit import record_event_audit
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    order_id = event.payload.get("order_id")
    if not order_id:
        return
    record_event_audit(
        module="event_bus",
        action=event.name,
        entity_type="order",
        entity_id=int(order_id),
        actor_id=event.actor_id,
        description=f"Order preparation started via event. order_id={order_id}",
        occurred_at=event.occurred_at,
    )
