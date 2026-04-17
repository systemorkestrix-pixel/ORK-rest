from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryZonePricingListOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_delivery_zone_pricing(
        self,
        *,
        search: str | None = None,
        active_only: bool | None = None,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    search: str | None = None
    active_only: bool | None = None


@dataclass
class Output:
    result: DeliveryZonePricingListOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    result = repo.list_delivery_zone_pricing(search=data.search, active_only=data.active_only)
    return Output(result=DeliveryZonePricingListOut(**result))
