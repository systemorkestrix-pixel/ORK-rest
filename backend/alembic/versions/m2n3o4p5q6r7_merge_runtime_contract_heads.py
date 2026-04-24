"""merge runtime contract head with delivery pricing head

Revision ID: m2n3o4p5q6r7
Revises: 0a1e2e9b1656, l1f2a3b4c5d6
Create Date: 2026-04-23 21:35:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "m2n3o4p5q6r7"
down_revision: Union[str, Sequence[str], None] = ("0a1e2e9b1656", "l1f2a3b4c5d6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
