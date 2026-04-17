from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseStockCountOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_stock_counts(self, *, offset: int, limit: int) -> list[dict[str, object]]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[WarehouseStockCountOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    counts = repo.list_stock_counts(offset=offset, limit=data.page_size)
    return Output(result=counts)
