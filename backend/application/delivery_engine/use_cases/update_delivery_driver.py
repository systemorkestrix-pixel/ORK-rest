from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.enums import DriverStatus
from app.models import DeliveryDriver
from app.schemas import DeliveryDriverOut, DeliveryDriverUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_delivery_driver(
        self,
        *,
        driver_id: int,
        provider_id: int | None,
        name: str,
        phone: str,
        vehicle: str | None,
        active: bool,
        status: DriverStatus,
    ) -> DeliveryDriver:
        ...


@dataclass
class Input:
    actor_id: int
    driver_id: int
    payload: DeliveryDriverUpdate


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
        driver = repo.update_delivery_driver(
            driver_id=data.driver_id,
            provider_id=data.payload.provider_id,
            name=data.payload.name,
            phone=data.payload.phone,
            vehicle=data.payload.vehicle,
            active=data.payload.active,
            status=data.payload.status,
        )
    return Output(result=driver)
