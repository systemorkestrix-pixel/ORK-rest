from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def delete_table(self, *, table_id: int) -> None:
        ...


@dataclass
class Input:
    actor_id: int
    table_id: int


@dataclass
class Output:
    result: object | None = None


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        repo.delete_table(table_id=data.table_id)
    return Output(result=None)
