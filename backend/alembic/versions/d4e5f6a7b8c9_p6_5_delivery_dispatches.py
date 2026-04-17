"""p6_5 delivery dispatches

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-03-29 00:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "d4e5f6a7b8c9"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "delivery_dispatches" not in existing_tables:
        op.create_table(
            "delivery_dispatches",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("provider_id", sa.Integer(), nullable=True),
            sa.Column("driver_id", sa.Integer(), nullable=True),
            sa.Column("dispatch_scope", sa.String(length=16), nullable=False, server_default="provider"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="offered"),
            sa.Column("channel", sa.String(length=16), nullable=False, server_default="console"),
            sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("responded_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["driver_id"], ["delivery_drivers.id"]),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
            sa.ForeignKeyConstraint(["provider_id"], ["delivery_providers.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = inspect(bind)

    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes("delivery_dispatches")
    }

    indexes = [
        ("ix_delivery_dispatches_id", ["id"]),
        ("ix_delivery_dispatches_order_id", ["order_id"]),
        ("ix_delivery_dispatches_provider_id", ["provider_id"]),
        ("ix_delivery_dispatches_driver_id", ["driver_id"]),
        ("ix_delivery_dispatches_dispatch_scope", ["dispatch_scope"]),
        ("ix_delivery_dispatches_status", ["status"]),
        ("ix_delivery_dispatches_channel", ["channel"]),
        ("ix_delivery_dispatches_sent_at", ["sent_at"]),
        ("ix_delivery_dispatches_responded_at", ["responded_at"]),
        ("ix_delivery_dispatches_expires_at", ["expires_at"]),
        ("ix_delivery_dispatches_created_by", ["created_by"]),
        ("ix_delivery_dispatches_order_status_id", ["order_id", "status", "id"]),
        ("ix_delivery_dispatches_driver_status_id", ["driver_id", "status", "id"]),
        ("ix_delivery_dispatches_provider_status_id", ["provider_id", "status", "id"]),
    ]
    for index_name, columns in indexes:
        if index_name not in existing_indexes:
            op.create_index(index_name, "delivery_dispatches", columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_delivery_dispatches_provider_status_id", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_driver_status_id", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_order_status_id", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_created_by", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_expires_at", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_responded_at", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_sent_at", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_channel", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_status", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_dispatch_scope", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_driver_id", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_provider_id", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_order_id", table_name="delivery_dispatches")
    op.drop_index("ix_delivery_dispatches_id", table_name="delivery_dispatches")
    op.drop_table("delivery_dispatches")
