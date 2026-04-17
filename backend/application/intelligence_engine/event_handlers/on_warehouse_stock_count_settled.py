"""
Event Handler: WAREHOUSE_STOCK_COUNT_SETTLED
"""
import logging

from application._shared.event_audit import record_event_audit
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    count_id = event.payload.get("count_id")
    if not count_id:
        return
    record_event_audit(
        module="event_bus",
        action=event.name,
        entity_type="warehouse_stock_count",
        entity_id=int(count_id),
        actor_id=event.actor_id,
        description=f"Warehouse stock count settled via event. count_id={count_id}",
        occurred_at=event.occurred_at,
    )
