from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import RestaurantTable
from app.schemas import ManagerTableOut, TableUpdateInput


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_table(self, *, table_id: int, status_value: str) -> RestaurantTable:
        ...


@dataclass
class Input:
    actor_id: int
    table_id: int
    payload: TableUpdateInput


@dataclass
class Output:
    result: ManagerTableOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        table = repo.update_table(table_id=data.table_id, status_value=data.payload.status.value)
    return Output(result=table)
