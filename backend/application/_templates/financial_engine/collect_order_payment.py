"""
Use Case: CollectOrderPayment (Financial Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class FinancialRepository(Protocol):
    def collect_order_payment(self, *args, **kwargs):
        ...


@dataclass
class Input:
    order_id: int
    collected_by: int
    amount_received: float | None = None


@dataclass
class Output:
    order_id: int
    payment_status: str


def execute(*, data: Input, repo: FinancialRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        order = repo.collect_order_payment(data)
    return Output(order_id=int(order.id), payment_status=str(order.payment_status))
