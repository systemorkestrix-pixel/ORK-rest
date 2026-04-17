"""
Repository Template

Rules:
- No business logic.
- CRUD only.
- Keep SQLAlchemy usage isolated here.
"""

from typing import Protocol, Iterable


class Repository(Protocol):
    def create(self, *args, **kwargs):
        ...

    def get(self, *args, **kwargs):
        ...

    def update(self, *args, **kwargs):
        ...

    def list(self, *args, **kwargs) -> Iterable:
        ...
