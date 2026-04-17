from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliveryProvider
from app.schemas import DeliveryProviderOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_delivery_providers(self) -> list[DeliveryProvider]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: list[DeliveryProviderOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    return Output(result=repo.list_delivery_providers())
