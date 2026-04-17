from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.enums import ProductKind
from app.models import Product
from app.schemas import ProductConsumptionComponentInput, ProductCreate, ProductOut, ProductSecondaryLinkInput
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def create_product(
        self,
        *,
        name: str,
        description: str | None,
        price: float,
        kind: ProductKind,
        available: bool,
        category_id: int | None,
        secondary_links: list[ProductSecondaryLinkInput],
        consumption_components: list[ProductConsumptionComponentInput],
    ) -> Product:
        ...


@dataclass
class Input:
    payload: ProductCreate


@dataclass
class Output:
    result: ProductOut


def execute(
    *,
    data: Input,
    repo: Repository,
    transaction_scope: TransactionScope,
    event_bus: EventBus | None = None,
) -> Output:
    with transaction_scope():
        product = repo.create_product(
            name=data.payload.name,
            description=data.payload.description,
            price=data.payload.price,
            kind=data.payload.kind,
            available=data.payload.available,
            category_id=data.payload.category_id,
            secondary_links=data.payload.secondary_links,
            consumption_components=data.payload.consumption_components,
        )
    return Output(result=product)
