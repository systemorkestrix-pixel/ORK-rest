from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import TelegramBotSettingsOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_telegram_bot_settings(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


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
    del data, transaction_scope, event_bus
    return Output(result=TelegramBotSettingsOut(**repo.get_telegram_bot_settings()))
