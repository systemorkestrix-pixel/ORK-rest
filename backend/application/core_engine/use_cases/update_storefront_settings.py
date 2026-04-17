from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import StorefrontSettingsOut, StorefrontSettingsUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_storefront_settings(
        self,
        *,
        brand_name: str,
        brand_mark: str,
        brand_icon: str,
        brand_tagline: str | None,
        socials: list[dict[str, object]],
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: StorefrontSettingsUpdate


@dataclass
class Output:
    result: StorefrontSettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        result = repo.update_storefront_settings(
            brand_name=data.payload.brand_name,
            brand_mark=data.payload.brand_mark,
            brand_icon=data.payload.brand_icon,
            brand_tagline=data.payload.brand_tagline,
            socials=[row.model_dump() for row in data.payload.socials],
            actor_id=data.actor_id,
        )
    return Output(result=StorefrontSettingsOut(**result))
