from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def archive_product(self, *, product_id: int) -> None:
        ...


@dataclass
class Input:
    product_id: int


@dataclass
class Output:
    result: object | None = None


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        repo.archive_product(product_id=data.product_id)
    return Output(result=None)
