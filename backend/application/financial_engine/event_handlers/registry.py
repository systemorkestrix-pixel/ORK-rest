"""
Event Handlers Registry
"""
from core.events.event_bus import EventBus
from core.events.event_types import EventTypes


from .on_order_delivered import handle as handle_order_delivered
from .on_delivery_completed import handle as handle_delivery_completed
from .on_delivery_settlement_created import handle as handle_delivery_settlement_created
from .on_warehouse_inbound_posted import handle as handle_warehouse_inbound_posted
from .on_warehouse_outbound_posted import handle as handle_warehouse_outbound_posted

def register(event_bus: EventBus) -> None:
    event_bus.subscribe(EventTypes.ORDER_DELIVERED, handle_order_delivered)
    event_bus.subscribe(EventTypes.DELIVERY_COMPLETED, handle_delivery_completed)
    event_bus.subscribe(EventTypes.DELIVERY_SETTLEMENT_CREATED, handle_delivery_settlement_created)
    event_bus.subscribe(EventTypes.WAREHOUSE_INBOUND_POSTED, handle_warehouse_inbound_posted)
    event_bus.subscribe(EventTypes.WAREHOUSE_OUTBOUND_POSTED, handle_warehouse_outbound_posted)
