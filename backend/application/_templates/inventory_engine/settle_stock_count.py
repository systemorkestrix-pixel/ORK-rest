"""
Use Case: SettleStockCount (Inventory Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class WarehouseRepository(Protocol):
    def settle_stock_count(self, *args, **kwargs):
        ...


@dataclass
class Input:
    count_id: int
    actor_id: int


@dataclass
class Output:
    count_id: int
    status: str


def execute(*, data: Input, repo: WarehouseRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        result = repo.settle_stock_count(data)
    return Output(count_id=int(result["id"]), status=str(result["status"]))
