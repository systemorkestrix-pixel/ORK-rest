"""
Event Handler: SHIFT_CLOSED
"""
import logging

from application._shared.event_audit import record_event_audit
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    shift_id = event.payload.get("shift_id")
    if not shift_id:
        return
    record_event_audit(
        module="event_bus",
        action=event.name,
        entity_type="shift_closure",
        entity_id=int(shift_id),
        actor_id=event.actor_id,
        description=f"Shift closed via event. shift_id={shift_id}",
        occurred_at=event.occurred_at,
    )
