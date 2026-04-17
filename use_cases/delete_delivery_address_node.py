from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def delete_delivery_address_node(self, *, node_id: int) -> None:
        ...


@dataclass
class Input:
    node_id: int


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
        repo.delete_delivery_address_node(node_id=data.node_id)
    return Output(result=None)
