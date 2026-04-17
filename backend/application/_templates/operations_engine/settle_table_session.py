"""
Use Case: SettleTableSession (Operations Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class TableRepository(Protocol):
    def settle_session(self, *args, **kwargs):
        ...


@dataclass
class Input:
    table_id: int
    performed_by: int
    amount_received: float | None = None


@dataclass
class Output:
    table_id: int
    settled_total: float
    amount_received: float
    change_amount: float


def execute(*, data: Input, repo: TableRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        result = repo.settle_session(data)
    return Output(
        table_id=int(result["table_id"]),
        settled_total=float(result["settled_total"]),
        amount_received=float(result["amount_received"]),
        change_amount=float(result["change_amount"]),
    )
