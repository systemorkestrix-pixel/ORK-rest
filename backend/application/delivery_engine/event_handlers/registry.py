"""
Event Handlers Registry
"""
from core.events.event_bus import EventBus
from core.events.event_types import EventTypes


from .on_order_preparation_started import handle as handle_order_preparation_started
from .on_order_ready import handle as handle_order_ready

def register(event_bus: EventBus) -> None:
    event_bus.subscribe(EventTypes.ORDER_PREPARATION_STARTED, handle_order_preparation_started)
    event_bus.subscribe(EventTypes.ORDER_READY, handle_order_ready)
