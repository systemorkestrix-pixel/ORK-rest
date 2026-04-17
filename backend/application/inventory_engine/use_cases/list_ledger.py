from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseLedgerOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_ledger(
        self,
        *,
        offset: int,
        limit: int,
        item_id: int | None,
        movement_kind: str | None,
    ) -> list[dict[str, object]]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50
    item_id: int | None = None
    movement_kind: str | None = None


@dataclass
class Output:
    result: list[WarehouseLedgerOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    rows = repo.list_ledger(
        offset=offset,
        limit=data.page_size,
        item_id=data.item_id,
        movement_kind=data.movement_kind,
    )
    return Output(result=rows)
