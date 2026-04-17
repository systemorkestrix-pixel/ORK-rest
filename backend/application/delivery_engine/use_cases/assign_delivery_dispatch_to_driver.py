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
    def assign_delivery_dispatch_to_driver(
        self,
        *,
        dispatch_id: int,
        driver_id: int,
        actor_id: int,
    ) -> DeliveryDispatch:
        ...


@dataclass
class Input:
    actor_id: int
    dispatch_id: int
    driver_id: int


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
        dispatch = repo.assign_delivery_dispatch_to_driver(
            dispatch_id=data.dispatch_id,
            driver_id=data.driver_id,
            actor_id=data.actor_id,
        )
    return Output(result=dispatch)
