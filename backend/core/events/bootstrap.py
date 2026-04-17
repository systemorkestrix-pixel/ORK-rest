from __future__ import annotations

from core.events.event_bus import EventBus

from application.delivery_engine.event_handlers.registry import register as register_delivery
from application.financial_engine.event_handlers.registry import register as register_financial
from application.intelligence_engine.event_handlers.registry import register as register_intelligence
from application.inventory_engine.event_handlers.registry import register as register_inventory
from application.kitchen_engine.event_handlers.registry import register as register_kitchen
from application.operations_engine.event_handlers.registry import register as register_operations

_EVENT_BUS: EventBus | None = None


def build_event_bus() -> EventBus:
    event_bus = EventBus()
    register_operations(event_bus)
    register_kitchen(event_bus)
    register_delivery(event_bus)
    register_inventory(event_bus)
    register_financial(event_bus)
    register_intelligence(event_bus)
    return event_bus


def get_event_bus() -> EventBus:
    global _EVENT_BUS
    if _EVENT_BUS is None:
        _EVENT_BUS = build_event_bus()
    return _EVENT_BUS
