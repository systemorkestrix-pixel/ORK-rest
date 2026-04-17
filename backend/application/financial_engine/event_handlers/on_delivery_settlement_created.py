"""
Event Handler: DELIVERY_SETTLEMENT_CREATED
"""
import logging

from application._shared.event_audit import record_event_audit
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    settlement_id = event.payload.get("settlement_id")
    if not settlement_id:
        return
    record_event_audit(
        module="event_bus",
        action=event.name,
        entity_type="delivery_settlement",
        entity_id=int(settlement_id),
        actor_id=event.actor_id,
        description=f"Delivery settlement created via event. settlement_id={settlement_id}",
        occurred_at=event.occurred_at,
    )
