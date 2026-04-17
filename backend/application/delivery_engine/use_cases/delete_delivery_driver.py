from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def delete_delivery_driver(self, *, driver_id: int) -> None:
        ...


@dataclass
class Input:
    driver_id: int


@dataclass
class Output:
    result: None


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        repo.delete_delivery_driver(driver_id=data.driver_id)
    return Output(result=None)
