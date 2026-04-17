from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryLocationPricingQuoteOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def quote_delivery_location_pricing(self, *, location_key: str | None) -> dict[str, object]:
        ...


@dataclass
class Input:
    location_key: str | None = None


@dataclass
class Output:
    result: DeliveryLocationPricingQuoteOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    return Output(result=DeliveryLocationPricingQuoteOut(**repo.quote_delivery_location_pricing(location_key=data.location_key)))
