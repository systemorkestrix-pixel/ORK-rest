from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import OrderOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_active_orders(self, *, limit: int) -> list[Order]:
        ...


@dataclass
class Input:
    limit: int = 200


@dataclass
class Output:
    result: list[OrderOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    orders = repo.list_active_orders(limit=data.limit)
    return Output(result=orders)
