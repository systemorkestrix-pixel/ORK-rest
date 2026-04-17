"""p4_2_drop_delivery_commission_rate

Revision ID: b4c2d7e9f0a1
Revises: a12e6f7b8c90
Create Date: 2026-03-15 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4c2d7e9f0a1"
down_revision: Union[str, Sequence[str], None] = "a12e6f7b8c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("delivery_drivers", schema=None) as batch_op:
        batch_op.drop_column("commission_rate")


def downgrade() -> None:
    with op.batch_alter_table("delivery_drivers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("commission_rate", sa.Float(), nullable=False, server_default="0"))
