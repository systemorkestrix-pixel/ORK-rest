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
    def list_delivery_drivers(self, *, offset: int, limit: int) -> list[DeliveryDriver]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50


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
    offset = (data.page - 1) * data.page_size
    items = repo.list_delivery_drivers(offset=offset, limit=data.page_size)
    return Output(result=items)
