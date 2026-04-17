from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import DeliveryLocationProviderSettingsOut, DeliveryLocationProviderSettingsUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_delivery_location_provider_settings(
        self,
        *,
        provider: str,
        enabled: bool,
        geonames_username: str | None,
        country_codes: list[str],
        cache_ttl_hours: int,
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: DeliveryLocationProviderSettingsUpdate


@dataclass
class Output:
    result: DeliveryLocationProviderSettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        result = repo.update_delivery_location_provider_settings(
            provider=data.payload.provider,
            enabled=data.payload.enabled,
            geonames_username=data.payload.geonames_username,
            country_codes=list(data.payload.country_codes),
            cache_ttl_hours=int(data.payload.cache_ttl_hours),
            actor_id=data.actor_id,
        )
    return Output(result=DeliveryLocationProviderSettingsOut(**result))
