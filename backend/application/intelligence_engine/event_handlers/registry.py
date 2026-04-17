"""
Event Handlers Registry
"""
from core.events.event_bus import EventBus
from core.events.event_types import EventTypes


from .on_order_created import handle as handle_order_created
from .on_order_preparation_started import handle as handle_order_preparation_started
from .on_order_out_for_delivery import handle as handle_order_out_for_delivery
from .on_order_delivered import handle as handle_order_delivered
from .on_order_canceled import handle as handle_order_canceled
from .on_warehouse_stock_count_settled import handle as handle_warehouse_stock_count_settled
from .on_financial_transaction_created import handle as handle_financial_transaction_created
from .on_shift_closed import handle as handle_shift_closed
from .on_expense_approved import handle as handle_expense_approved
from .on_system_audit_recorded import handle as handle_system_audit_recorded
from .on_security_audit_recorded import handle as handle_security_audit_recorded

def register(event_bus: EventBus) -> None:
    event_bus.subscribe(EventTypes.ORDER_CREATED, handle_order_created)
    event_bus.subscribe(EventTypes.ORDER_PREPARATION_STARTED, handle_order_preparation_started)
    event_bus.subscribe(EventTypes.ORDER_OUT_FOR_DELIVERY, handle_order_out_for_delivery)
    event_bus.subscribe(EventTypes.ORDER_DELIVERED, handle_order_delivered)
    event_bus.subscribe(EventTypes.ORDER_CANCELED, handle_order_canceled)
    event_bus.subscribe(EventTypes.WAREHOUSE_STOCK_COUNT_SETTLED, handle_warehouse_stock_count_settled)
    event_bus.subscribe(EventTypes.FINANCIAL_TRANSACTION_CREATED, handle_financial_transaction_created)
    event_bus.subscribe(EventTypes.SHIFT_CLOSED, handle_shift_closed)
    event_bus.subscribe(EventTypes.EXPENSE_APPROVED, handle_expense_approved)
    event_bus.subscribe(EventTypes.SYSTEM_AUDIT_RECORDED, handle_system_audit_recorded)
    event_bus.subscribe(EventTypes.SECURITY_AUDIT_RECORDED, handle_security_audit_recorded)
