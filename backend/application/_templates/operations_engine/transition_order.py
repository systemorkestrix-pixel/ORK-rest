"""
Use Case: TransitionOrder (Operations Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class OrderRepository(Protocol):
    def transition(self, *args, **kwargs):
        ...


@dataclass
class Input:
    order_id: int
    target_status: str
    performed_by: int
    amount_received: float | None = None
    collect_payment: bool = True
    reason_code: str | None = None
    reason_note: str | None = None


@dataclass
class Output:
    order_id: int
    status: str


def execute(*, data: Input, repo: OrderRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        order = repo.transition(data)
    return Output(order_id=int(order.id), status=order.status)
