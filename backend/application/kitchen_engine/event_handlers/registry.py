"""
Event Handlers Registry
"""
from core.events.event_bus import EventBus
from core.events.event_types import EventTypes


from .on_order_confirmed import handle as handle_order_confirmed
from .on_order_sent_to_kitchen import handle as handle_order_sent_to_kitchen

def register(event_bus: EventBus) -> None:
    event_bus.subscribe(EventTypes.ORDER_CONFIRMED, handle_order_confirmed)
    event_bus.subscribe(EventTypes.ORDER_SENT_TO_KITCHEN, handle_order_sent_to_kitchen)
