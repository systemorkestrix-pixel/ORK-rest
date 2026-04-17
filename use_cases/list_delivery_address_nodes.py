from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryAddressNodeListOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_delivery_address_nodes(
        self,
        *,
        parent_id: int | None = None,
        public_only: bool = False,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    parent_id: int | None = None
    public_only: bool = False


@dataclass
class Output:
    result: DeliveryAddressNodeListOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    result = repo.list_delivery_address_nodes(parent_id=data.parent_id, public_only=data.public_only)
    return Output(result=DeliveryAddressNodeListOut(**result))
