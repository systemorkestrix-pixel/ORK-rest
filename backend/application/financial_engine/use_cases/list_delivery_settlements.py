from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliverySettlement
from app.schemas import DeliverySettlementOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_delivery_settlements(self, *, offset: int, limit: int) -> list[DeliverySettlement]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[DeliverySettlementOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    rows = repo.list_delivery_settlements(offset=offset, limit=data.page_size)
    return Output(result=rows)
