from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Product
from app.schemas import ProductOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_products(self, *, kind: str, offset: int, limit: int) -> list[Product]:
        ...


@dataclass
class Input:
    kind: str = "all"
    page: int = 1
    page_size: int = 50


@dataclass
class Output:
    result: list[ProductOut]


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    offset = (data.page - 1) * data.page_size
    items = repo.list_products(kind=data.kind, offset=offset, limit=data.page_size)
    return Output(result=items)
