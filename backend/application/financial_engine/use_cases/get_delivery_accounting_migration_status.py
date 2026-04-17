from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryAccountingMigrationStatusOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_delivery_accounting_migration_status(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: DeliveryAccountingMigrationStatusOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    status_payload = repo.get_delivery_accounting_migration_status()
    return Output(result=status_payload)
