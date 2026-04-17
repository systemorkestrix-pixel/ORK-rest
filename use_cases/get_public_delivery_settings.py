from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliverySettingsOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_delivery_settings(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: DeliverySettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    settings = repo.get_delivery_settings()
    return Output(result=DeliverySettingsOut(**settings))
