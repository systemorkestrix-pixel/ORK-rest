from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import WarehouseStockCountOut
from core.events.event_bus import EventBus, build_event
from core.events.event_types import EventTypes


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def settle_stock_count(self, *, count_id: int, actor_id: int) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    count_id: int


@dataclass
class Output:
    result: WarehouseStockCountOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        count_doc = repo.settle_stock_count(count_id=data.count_id, actor_id=data.actor_id)

    if event_bus is not None:
        event_bus.publish(
            build_event(
                name=EventTypes.WAREHOUSE_STOCK_COUNT_SETTLED,
                payload={
                    "count_id": int(count_doc.get("id")),
                    "count_no": count_doc.get("count_no"),
                    "status": count_doc.get("status"),
                },
                actor_id=data.actor_id,
            )
        )

    return Output(result=count_doc)
