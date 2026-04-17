"""
Use Case: CloseShift (Financial Engine)
"""
from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


class FinancialRepository(Protocol):
    def close_shift(self, *args, **kwargs):
        ...


@dataclass
class Input:
    opening_cash: float
    actual_cash: float
    note: str | None = None
    closed_by: int | None = None


@dataclass
class Output:
    shift_id: int
    business_date: str
    variance: float


def execute(*, data: Input, repo: FinancialRepository, transaction_scope: TransactionScope) -> Output:
    with transaction_scope():
        shift = repo.close_shift(data)
    return Output(
        shift_id=int(shift.id),
        business_date=str(shift.business_date),
        variance=float(shift.variance),
    )
