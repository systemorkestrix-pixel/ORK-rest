from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Product
from app.schemas import PublicProductOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_public_products(self, *, offset: int, limit: int) -> list[Product]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 24


@dataclass
class Output:
    result: list[PublicProductOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    items = repo.list_public_products(offset=offset, limit=data.page_size)
    return Output(result=items)
