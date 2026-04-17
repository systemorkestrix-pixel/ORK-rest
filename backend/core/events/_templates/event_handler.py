"""
Event Handler Template

Rules:
- Must be idempotent.
- No direct DB access unless through repositories.
"""

from typing import Protocol
from backend.core.events.event_bus import DomainEvent


class Repository(Protocol):
    # TODO: define repository interface
    pass


def handle(event: DomainEvent, repo: Repository) -> None:
    # TODO: implement handler logic
    # Event payload is event.payload
    pass
