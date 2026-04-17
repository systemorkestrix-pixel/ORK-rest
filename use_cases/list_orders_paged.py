from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.enums import OrderStatus, OrderType
from app.models import Order
from app.schemas import OrdersPageOut, OrderOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def list_orders_paged(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_direction: str,
        status_filter: str | None,
        order_type: str | None,
    ) -> tuple[list[Order], int]:
        ...


@dataclass
class Input:
    page: int = 1
    page_size: int = 12
    search: str | None = None
    sort_by: str = "created_at"
    sort_direction: str = "desc"
    status_filter: OrderStatus | None = None
    order_type: OrderType | None = None


@dataclass
class Output:
    result: OrdersPageOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    items, total = repo.list_orders_paged(
        page=data.page,
        page_size=data.page_size,
        search=data.search,
        sort_by=data.sort_by,
        sort_direction=data.sort_direction,
        status_filter=data.status_filter.value if data.status_filter else None,
        order_type=data.order_type.value if data.order_type else None,
    )
    return Output(
        result=OrdersPageOut(
            items=items,
            total=total,
            page=data.page,
            page_size=data.page_size,
        )
    )
