"""p6_6 delivery failure resolution

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("delivery_failure_resolution_status", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("delivery_failure_resolution_note", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("delivery_failure_resolved_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("delivery_failure_resolved_by", sa.Integer(), nullable=True))
        batch_op.create_index("ix_orders_delivery_failure_resolution_status", ["delivery_failure_resolution_status"], unique=False)
        batch_op.create_index("ix_orders_delivery_failure_resolved_at", ["delivery_failure_resolved_at"], unique=False)
        batch_op.create_index("ix_orders_delivery_failure_resolved_by", ["delivery_failure_resolved_by"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_delivery_failure_resolved_by")
        batch_op.drop_index("ix_orders_delivery_failure_resolved_at")
        batch_op.drop_index("ix_orders_delivery_failure_resolution_status")
        batch_op.drop_column("delivery_failure_resolved_by")
        batch_op.drop_column("delivery_failure_resolved_at")
        batch_op.drop_column("delivery_failure_resolution_note")
        batch_op.drop_column("delivery_failure_resolution_status")
