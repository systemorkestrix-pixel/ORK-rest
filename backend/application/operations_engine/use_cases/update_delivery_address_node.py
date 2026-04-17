from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryAddressNodeOut, DeliveryAddressNodeUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_delivery_address_node(
        self,
        *,
        node_id: int,
        code: str,
        name: str,
        display_name: str,
        postal_code: str | None,
        notes: str | None,
        active: bool,
        visible_in_public: bool,
        sort_order: int,
        actor_id: int,
    ):
        ...

    def list_delivery_address_nodes(
        self,
        *,
        parent_id: int | None = None,
        public_only: bool = False,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    node_id: int
    payload: DeliveryAddressNodeUpdate


@dataclass
class Output:
    result: DeliveryAddressNodeOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        node = repo.update_delivery_address_node(
            node_id=data.node_id,
            code=data.payload.code,
            name=data.payload.name,
            display_name=data.payload.display_name,
            postal_code=data.payload.postal_code,
            notes=data.payload.notes,
            active=data.payload.active,
            visible_in_public=data.payload.visible_in_public,
            sort_order=int(data.payload.sort_order),
            actor_id=data.actor_id,
        )
    listing = repo.list_delivery_address_nodes(parent_id=node.parent_id, public_only=False)
    row = next(item for item in listing["items"] if int(item["id"]) == int(node.id))
    return Output(result=DeliveryAddressNodeOut(**row))
