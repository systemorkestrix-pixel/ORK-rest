from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import ProductCategory
from app.schemas import ProductCategoryOut, ProductCategoryUpdate
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def update_product_category(
        self,
        *,
        category_id: int,
        name: str,
        active: bool,
        sort_order: int,
    ) -> ProductCategory:
        ...


@dataclass
class Input:
    category_id: int
    payload: ProductCategoryUpdate


@dataclass
class Output:
    result: ProductCategoryOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        category = repo.update_product_category(
            category_id=data.category_id,
            name=data.payload.name,
            active=data.payload.active,
            sort_order=data.payload.sort_order,
        )
    return Output(result=category)
