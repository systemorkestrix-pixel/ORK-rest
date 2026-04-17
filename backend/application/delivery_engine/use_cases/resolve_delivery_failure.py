from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import DeliveryFailureResolutionInput, OrderOut


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def resolve_delivery_failure(
        self,
        *,
        order_id: int,
        performed_by: int,
        resolution_action: str,
        resolution_note: str | None,
    ) -> Order:
        ...


@dataclass
class Input:
    actor_id: int
    order_id: int
    payload: DeliveryFailureResolutionInput


@dataclass
class Output:
    result: OrderOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus=None,
) -> Output:
    del event_bus
    with transaction_scope():
        order = repo.resolve_delivery_failure(
            order_id=data.order_id,
            performed_by=data.actor_id,
            resolution_action=data.payload.resolution_action,
            resolution_note=data.payload.resolution_note,
        )
    return Output(result=order)
