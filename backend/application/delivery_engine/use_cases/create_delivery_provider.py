from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import DeliveryProvider
from app.schemas import DeliveryProviderCreate, DeliveryProviderOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_delivery_provider(
        self,
        *,
        account_user_id: int | None,
        name: str,
        provider_type: str,
        active: bool,
    ) -> DeliveryProvider:
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliveryProviderCreate


@dataclass
class Output:
    result: DeliveryProviderOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        provider = repo.create_delivery_provider(
            account_user_id=data.payload.account_user_id,
            name=data.payload.name,
            provider_type=data.payload.provider_type,
            active=data.payload.active,
        )
    return Output(result=provider)
