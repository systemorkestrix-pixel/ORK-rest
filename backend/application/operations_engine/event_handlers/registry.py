"""
Event Handlers Registry
"""
from core.events.event_bus import EventBus
from core.events.event_types import EventTypes


from .on_driver_assigned import handle as handle_driver_assigned
from .on_driver_departed import handle as handle_driver_departed
from .on_delivery_failed import handle as handle_delivery_failed

def register(event_bus: EventBus) -> None:
    event_bus.subscribe(EventTypes.DRIVER_ASSIGNED, handle_driver_assigned)
    event_bus.subscribe(EventTypes.DRIVER_DEPARTED, handle_driver_departed)
    event_bus.subscribe(EventTypes.DELIVERY_FAILED, handle_delivery_failed)
