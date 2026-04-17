from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryLocationListOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_delivery_location_children(self, *, parent_key: str) -> dict[str, object]:
        ...


@dataclass
class Input:
    parent_key: str


@dataclass
class Output:
    result: DeliveryLocationListOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    return Output(result=DeliveryLocationListOut(**repo.list_delivery_location_children(parent_key=data.parent_key)))
