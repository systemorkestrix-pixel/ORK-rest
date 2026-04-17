from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryZonePricingOut, DeliveryZonePricingUpsert
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def upsert_delivery_zone_pricing(
        self,
        *,
        node_id: int,
        delivery_fee: float,
        active: bool,
        sort_order: int,
        actor_id: int,
    ):
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliveryZonePricingUpsert


@dataclass
class Output:
    result: DeliveryZonePricingOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        zone = repo.upsert_delivery_zone_pricing(
            node_id=int(data.payload.node_id),
            delivery_fee=float(data.payload.delivery_fee),
            active=bool(data.payload.active),
            sort_order=int(data.payload.sort_order),
            actor_id=data.actor_id,
        )
    return Output(result=DeliveryZonePricingOut.model_validate(zone))
