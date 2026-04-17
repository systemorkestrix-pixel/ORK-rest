"""
Event Handler: SECURITY_AUDIT_RECORDED
"""
import logging

from application._shared.event_audit import record_event_audit
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    user_id = event.payload.get("user_id")
    if user_id is None:
        return
    record_event_audit(
        module="event_bus",
        action=event.name,
        entity_type="security_event",
        entity_id=int(user_id),
        actor_id=event.actor_id,
        description="Security audit recorded via event.",
        occurred_at=event.occurred_at,
    )
