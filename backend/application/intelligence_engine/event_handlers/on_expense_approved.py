"""
Event Handler: EXPENSE_APPROVED
"""
import logging

from application._shared.event_audit import record_event_audit
from core.events.event_bus import DomainEvent

logger = logging.getLogger(__name__)


def handle(event: DomainEvent) -> None:
    expense_id = event.payload.get("expense_id")
    if not expense_id:
        return
    record_event_audit(
        module="event_bus",
        action=event.name,
        entity_type="expense",
        entity_id=int(expense_id),
        actor_id=event.actor_id,
        description=f"Expense approved via event. expense_id={expense_id}",
        occurred_at=event.occurred_at,
    )
