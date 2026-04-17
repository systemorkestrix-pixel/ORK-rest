from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryHistoryOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_delivery_history(
        self,
        *,
        actor_id: int,
        offset: int,
        limit: int,
    ) -> list[DeliveryHistoryOut]:
        ...


@dataclass
class Input:
    actor_id: int
    page: int = 1
    page_size: int = 30


@dataclass
class Output:
    result: list[DeliveryHistoryOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    items = repo.list_delivery_history(
        actor_id=data.actor_id,
        offset=offset,
        limit=data.page_size,
    )
    return Output(result=items)
