from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Product
from app.schemas import ProductImageInput, ProductOut
from core.events.event_bus import EventBus


class TransactionScope(Protocol):
    def __call__(self):
        ...


class Repository(Protocol):
    def upload_product_image(
        self,
        *,
        product_id: int,
        data_base64: str,
        mime_type: str,
    ) -> Product:
        ...


@dataclass
class Input:
    product_id: int
    payload: ProductImageInput


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
        product = repo.upload_product_image(
            product_id=data.product_id,
            data_base64=data.payload.data_base64,
            mime_type=data.payload.mime_type,
        )
    return Output(result=product)
