"""
Event Bus Template (In-Memory)

Rules:
- No external dependencies.
- Handlers must be idempotent.
- Publish after transaction commit when possible.
"""

from dataclasses import dataclass
from typing import Any, Callable, DefaultDict
from collections import defaultdict
from datetime import datetime, UTC


@dataclass(frozen=True)
class DomainEvent:
    name: str
    payload: dict[str, Any]
    occurred_at: datetime
    correlation_id: str | None = None
    actor_id: int | None = None


Handler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: DefaultDict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(event.name, []):
            handler(event)


def build_event(
    *,
    name: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
    actor_id: int | None = None,
) -> DomainEvent:
    return DomainEvent(
        name=name,
        payload=payload,
        occurred_at=datetime.now(UTC),
        correlation_id=correlation_id,
        actor_id=actor_id,
    )
