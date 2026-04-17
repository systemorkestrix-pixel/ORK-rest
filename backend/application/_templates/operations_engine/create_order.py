"""
Use Case: CreateOrder (Operations Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class OrderRepository(Protocol):
    def create_order(self, *args, **kwargs):
        ...


@dataclass
class OrderItemInput:
    product_id: int
    quantity: int


@dataclass
class Input:
    order_type: str  # dine-in | takeaway | delivery
    items: list[OrderItemInput]
    table_id: int | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    created_by: int | None = None


@dataclass
class Output:
    order_id: int
    status: str


def execute(*, data: Input, repo: OrderRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        order = repo.create_order(data)
    return Output(order_id=int(order.id), status=order.status)
