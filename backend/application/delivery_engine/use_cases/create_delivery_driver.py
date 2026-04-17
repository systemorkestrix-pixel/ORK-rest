from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliveryDriver
from app.schemas import DeliveryDriverCreate, DeliveryDriverOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_delivery_driver(
        self,
        *,
        user_id: int | None,
        name: str,
        provider_id: int | None,
        phone: str,
        vehicle: str | None,
        active: bool,
    ) -> DeliveryDriver:
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliveryDriverCreate


@dataclass
class Output:
    result: DeliveryDriverOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        driver = repo.create_delivery_driver(
            user_id=data.payload.user_id,
            name=data.payload.name,
            provider_id=data.payload.provider_id,
            phone=data.payload.phone,
            vehicle=data.payload.vehicle,
            active=data.payload.active,
        )
    return Output(result=driver)
