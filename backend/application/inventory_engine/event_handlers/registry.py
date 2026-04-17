"""
Inventory Engine Event Handlers Registry
"""
from core.events.event_bus import EventBus
from core.events.event_types import EventTypes

from .on_order_confirmed import handle as handle_order_confirmed


def register(event_bus: EventBus) -> None:
    event_bus.subscribe(EventTypes.ORDER_CONFIRMED, handle_order_confirmed)
