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
    def reject_delivery_dispatch(
        self,
        *,
        dispatch_id: int,
        actor_id: int,
    ) -> DeliveryDispatch:
        ...


@dataclass
class Input:
    actor_id: int
    dispatch_id: int


@dataclass
class Output:
    result: DeliveryDispatchOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    del event_bus
    with transaction_scope():
        dispatch = repo.reject_delivery_dispatch(dispatch_id=data.dispatch_id, actor_id=data.actor_id)
    return Output(result=dispatch)
