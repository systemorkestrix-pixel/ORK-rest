from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import TableSessionSettlementInput, TableSessionSettlementOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def settle_table_session(
        self,
        *,
        table_id: int,
        performed_by: int,
        amount_received: float | None,
    ) -> TableSessionSettlementOut:
        ...


@dataclass
class Input:
    actor_id: int
    table_id: int
    payload: TableSessionSettlementInput


@dataclass
class Output:
    result: TableSessionSettlementOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        settlement = repo.settle_table_session(
            table_id=data.table_id,
            performed_by=data.actor_id,
            amount_received=data.payload.amount_received,
        )
    return Output(result=settlement)
