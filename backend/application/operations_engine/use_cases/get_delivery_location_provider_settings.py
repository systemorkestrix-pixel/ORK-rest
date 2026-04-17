from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryLocationProviderSettingsOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_delivery_location_provider_settings(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: DeliveryLocationProviderSettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    return Output(result=DeliveryLocationProviderSettingsOut(**repo.get_delivery_location_provider_settings()))
