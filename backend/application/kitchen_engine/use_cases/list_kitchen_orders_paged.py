from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Order
from app.schemas import KitchenOrdersPageOut, OrderOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_kitchen_orders_paged(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_direction: str,
        tie_break_direction: str,
        scope: str,
    ) -> tuple[list[Order], int, dict[str, int | float | str]]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 24
    search: str | None = None
    sort_by: str = "created_at"
    sort_direction: str = "asc"
    tie_break_direction: str = "asc"
    scope: str = "active"


@dataclass
class Output:
    result: KitchenOrdersPageOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    items, total, summary = repo.list_kitchen_orders_paged(
        page=data.page,
        page_size=data.page_size,
        search=data.search,
        sort_by=data.sort_by,
        sort_direction=data.sort_direction,
        tie_break_direction=data.tie_break_direction,
        scope=data.scope,
    )
    return Output(
        result=KitchenOrdersPageOut(
            items=items,
            total=total,
            page=data.page,
            page_size=data.page_size,
            scope=data.scope,
            summary=summary,
        )
    )
