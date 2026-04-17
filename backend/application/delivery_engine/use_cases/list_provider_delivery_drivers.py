from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliveryDriver
from app.schemas import DeliveryDriverOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_provider_delivery_drivers(
        self,
        *,
        actor_id: int,
    ) -> list[DeliveryDriver]:
        ...


@dataclass
class Input:
    actor_id: int


@dataclass
class Output:
    result: list[DeliveryDriverOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    del transaction_scope, event_bus
    return Output(result=repo.list_provider_delivery_drivers(actor_id=data.actor_id))
