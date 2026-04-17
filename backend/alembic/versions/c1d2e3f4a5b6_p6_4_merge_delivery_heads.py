"""p6_4 merge delivery heads

Revision ID: c1d2e3f4a5b6
Revises: a7b8c9d0e1f2, b7c8d9e0f1a2
Create Date: 2026-03-28 23:55:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = ("a7b8c9d0e1f2", "b7c8d9e0f1a2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
