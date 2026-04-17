from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import TelegramBotSettingsOut, TelegramBotSettingsUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_telegram_bot_settings(
        self,
        *,
        enabled: bool,
        bot_token: str | None,
        bot_username: str | None,
        actor_id: int,
    ) -> dict[str, object]:
        ...


@dataclass
class Input:
    actor_id: int
    payload: TelegramBotSettingsUpdate


@dataclass
class Output:
    result: TelegramBotSettingsOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    del event_bus
    with transaction_scope():
        result = repo.update_telegram_bot_settings(
            enabled=data.payload.enabled,
            bot_token=data.payload.bot_token,
            bot_username=data.payload.bot_username,
            actor_id=data.actor_id,
        )
    return Output(result=TelegramBotSettingsOut(**result))
