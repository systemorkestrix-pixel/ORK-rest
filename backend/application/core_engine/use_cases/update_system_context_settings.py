from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import SystemContextOut, SystemContextUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_system_context_settings(
        self,
        *,
        country_code: str,
        country_name: str,
        currency_code: str,
        currency_name: str,
        currency_symbol: str,
        currency_decimal_places: int,
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: SystemContextUpdate


@dataclass
class Output:
    result: SystemContextOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        result = repo.update_system_context_settings(
            country_code=data.payload.country_code,
            country_name=data.payload.country_name,
            currency_code=data.payload.currency_code,
            currency_name=data.payload.currency_name,
            currency_symbol=data.payload.currency_symbol,
            currency_decimal_places=int(data.payload.currency_decimal_places),
            actor_id=data.actor_id,
        )
    return Output(result=SystemContextOut(**result))
