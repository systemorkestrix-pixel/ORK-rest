from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseStockCountCreate, WarehouseStockCountOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_stock_count(
        self,
        *,
        note: str | None,
        idempotency_key: str | None,
        items: list[tuple[int, float]],
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: WarehouseStockCountCreate


@dataclass
class Output:
    result: WarehouseStockCountOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        count_doc = repo.create_stock_count(
            note=data.payload.note,
            idempotency_key=data.payload.idempotency_key,
            items=[(item.item_id, item.counted_quantity) for item in data.payload.items],
            actor_id=data.actor_id,
        )
    return Output(result=count_doc)
