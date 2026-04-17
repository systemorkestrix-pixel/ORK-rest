from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import TelegramBotHealthOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def get_telegram_bot_health(self) -> dict[str, object]:
        ...


@dataclass
class Input:
    pass


@dataclass
class Output:
    result: TelegramBotHealthOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    del data, transaction_scope, event_bus
    return Output(result=TelegramBotHealthOut(**repo.get_telegram_bot_health()))
