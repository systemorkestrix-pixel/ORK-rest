"""
Event Handler: SYSTEM_AUDIT_RECORDED
"""
import logging

from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    logger.debug(
        "System audit event observed: %s payload=%s correlation=%s actor=%s",
        event.name,
        event.payload,
        event.correlation_id,
        event.actor_id,
    )
