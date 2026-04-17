"""
Event Handler: ORDER_SENT_TO_KITCHEN
"""
import logging

from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    """
    Side-effect-free handler.
    Core state is mutated within Use Cases; handlers provide observability hooks.
    """
    logger.debug(
        "Event handled: %s payload=%s correlation=%s actor=%s",
        event.name,
        event.payload,
        event.correlation_id,
        event.actor_id,
    )
