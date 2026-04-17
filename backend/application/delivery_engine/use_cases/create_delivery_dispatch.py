from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliveryDispatch
from app.schemas import DeliveryDispatchCreate, DeliveryDispatchOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_delivery_dispatch(
        self,
        *,
        order_id: int,
        actor_id: int,
        provider_id: int | None,
        driver_id: int | None,
    ) -> DeliveryDispatch:
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliveryDispatchCreate


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
        dispatch = repo.create_delivery_dispatch(
            order_id=data.payload.order_id,
            actor_id=data.actor_id,
            provider_id=data.payload.provider_id,
            driver_id=data.payload.driver_id,
        )
    return Output(result=dispatch)
