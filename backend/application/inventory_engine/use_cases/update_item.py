from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import WarehouseItem
from app.schemas import WarehouseItemOut, WarehouseItemUpdate


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_item(
        self,
        *,
        item_id: int,
        name: str,
        unit: str,
        alert_threshold: float,
        active: bool,
    ) -> WarehouseItem:
        ...


@dataclass
class Input:
    actor_id: int
    item_id: int
    payload: WarehouseItemUpdate


@dataclass
class Output:
    result: WarehouseItemOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    with transaction_scope():
        item = repo.update_item(
            item_id=data.item_id,
            name=data.payload.name,
            unit=data.payload.unit,
            alert_threshold=data.payload.alert_threshold,
            active=data.payload.active,
        )
    return Output(result=item)
