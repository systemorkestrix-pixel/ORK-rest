from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import RestaurantTable
from app.schemas import ManagerTableOut, TableCreateInput


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_table(self, *, status_value: str) -> RestaurantTable:
        ...


@dataclass
class Input:
    actor_id: int
    payload: TableCreateInput


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
        table = repo.create_table(status_value=data.payload.status.value)
    return Output(result=table)
