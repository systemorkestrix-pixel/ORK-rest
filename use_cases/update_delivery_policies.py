from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryPolicySettingsOut, DeliveryPolicySettingsUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_delivery_policies(
        self,
        *,
        min_order_amount: float,
        auto_notify_team: bool,
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliveryPolicySettingsUpdate


@dataclass
class Output:
    result: DeliveryPolicySettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        values = repo.update_delivery_policies(
            min_order_amount=float(data.payload.min_order_amount),
            auto_notify_team=bool(data.payload.auto_notify_team),
            actor_id=data.actor_id,
        )
    return Output(result=DeliveryPolicySettingsOut(**values))
