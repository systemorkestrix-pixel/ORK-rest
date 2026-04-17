"""
Event Handler: WAREHOUSE_INBOUND_POSTED
"""
import logging

from application._shared.event_audit import record_event_audit
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    voucher_id = event.payload.get("voucher_id")
    if not voucher_id:
        return
    record_event_audit(
        module="event_bus",
        action=event.name,
        entity_type="warehouse_inbound_voucher",
        entity_id=int(voucher_id),
        actor_id=event.actor_id,
        description=f"Warehouse inbound posted via event. voucher_id={voucher_id}",
        occurred_at=event.occurred_at,
    )
