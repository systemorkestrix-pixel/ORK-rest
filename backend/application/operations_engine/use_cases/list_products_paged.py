from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Product
from app.schemas import ProductsPageOut, ProductOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_products_paged(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_direction: str,
        archive_state: str,
        kind: str,
    ) -> tuple[list[Product], int]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 12
    search: str | None = None
    sort_by: str = "id"
    sort_direction: str = "desc"
    archive_state: str = "all"
    kind: str = "all"


@dataclass
class Output:
    result: ProductsPageOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    items, total = repo.list_products_paged(
        page=data.page,
        page_size=data.page_size,
        search=data.search,
        sort_by=data.sort_by,
        sort_direction=data.sort_direction,
        archive_state=data.archive_state,
        kind=data.kind,
    )
    return Output(
        result=ProductsPageOut(
            items=items,
            total=total,
            page=data.page,
            page_size=data.page_size,
        )
    )
