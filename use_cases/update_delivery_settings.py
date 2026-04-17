from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliverySettingsOut, DeliverySettingsUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_delivery_settings(self, *, delivery_fee: float, actor_id: int) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliverySettingsUpdate


@dataclass
class Output:
    result: DeliverySettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        settings = repo.update_delivery_settings(
            delivery_fee=float(data.payload.delivery_fee),
            actor_id=data.actor_id,
        )
    return Output(result=DeliverySettingsOut(**settings))
