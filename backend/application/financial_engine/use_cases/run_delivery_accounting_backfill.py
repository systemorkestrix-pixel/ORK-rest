from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryAccountingBackfillInput, DeliveryAccountingBackfillOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def run_delivery_accounting_backfill(
        self,
        *,
        actor_id: int,
        limit: int,
        dry_run: bool,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliveryAccountingBackfillInput


@dataclass
class Output:
    result: DeliveryAccountingBackfillOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        result = repo.run_delivery_accounting_backfill(
            actor_id=data.actor_id,
            limit=data.payload.limit,
            dry_run=data.payload.dry_run,
        )
    return Output(result=result)
