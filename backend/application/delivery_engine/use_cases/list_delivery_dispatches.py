from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliveryDispatch
from app.schemas import DeliveryDispatchOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_delivery_dispatches(
        self,
        *,
        actor_id: int,
        actor_role: str,
        offset: int,
        limit: int,
    ) -> list[DeliveryDispatch]:
        ...


@dataclass
class Input:
    actor_id: int
    actor_role: str
    page: int = 1
    page_size: int = 30


@dataclass
class Output:
    result: list[DeliveryDispatchOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    del transaction_scope, event_bus
    offset = (data.page - 1) * data.page_size
    items = repo.list_delivery_dispatches(
        actor_id=data.actor_id,
        actor_role=data.actor_role,
        offset=offset,
        limit=data.page_size,
    )
    return Output(result=items)
