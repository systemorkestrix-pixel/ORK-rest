from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import SystemContextOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_system_context_settings(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: SystemContextOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    return Output(result=SystemContextOut(**repo.get_system_context_settings()))
