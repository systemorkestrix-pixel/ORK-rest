from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import OrderOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def notify_delivery_team(self, *, order_id: int, actor_id: int) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int


@dataclass
class Output:
    result: OrderOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        order = repo.notify_delivery_team(order_id=data.order_id, actor_id=data.actor_id)
    return Output(result=order)
