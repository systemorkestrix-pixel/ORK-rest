"""
Use Case Template

Rules:
- No direct SQLAlchemy usage here.
- Use repositories only.
- Must run inside transaction_scope when the operation is critical.
"""

from dataclasses import dataclass
from typing import Protocol


class TransactionScope(Protocol):
    def __call__(self):
        ...


@dataclass
class Input:
    # TODO: define input fields
    pass


@dataclass
class Output:
    # TODO: define output fields
    pass


class Repository(Protocol):
    # TODO: define repository interface methods
    pass


def execute(*, data: Input, repo: Repository, transaction_scope: TransactionScope) -> Output:
    # TODO: add validations
    # TODO: perform domain logic
    with transaction_scope():
        # TODO: repository operations
        pass
    # TODO: map to Output
    return Output()
