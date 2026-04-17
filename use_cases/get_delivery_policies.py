from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryPolicySettingsOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_delivery_policies(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


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
    values = repo.get_delivery_policies()
    return Output(
        result=DeliveryPolicySettingsOut(
            min_order_amount=float(values["min_order_amount"]),
            auto_notify_team=bool(values["auto_notify_team"]),
        )
    )
