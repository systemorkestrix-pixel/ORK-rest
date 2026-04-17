from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import KitchenRuntimeSettingsOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_kitchen_runtime_settings(self) -> dict[str, int | str]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: KitchenRuntimeSettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    settings = repo.get_kitchen_runtime_settings()
    return Output(result=settings)
