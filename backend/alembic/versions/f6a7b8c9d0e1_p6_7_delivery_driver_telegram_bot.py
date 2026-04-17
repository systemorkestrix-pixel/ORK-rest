"""p6.7 delivery driver telegram bot fields

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-28 21:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, "delivery_drivers")

    with op.batch_alter_table("delivery_drivers") as batch_op:
        if "telegram_chat_id" not in columns:
            batch_op.add_column(sa.Column("telegram_chat_id", sa.String(length=40), nullable=True))
        if "telegram_username" not in columns:
            batch_op.add_column(sa.Column("telegram_username", sa.String(length=120), nullable=True))
        if "telegram_link_code" not in columns:
            batch_op.add_column(sa.Column("telegram_link_code", sa.String(length=64), nullable=True))
        if "telegram_link_expires_at" not in columns:
            batch_op.add_column(sa.Column("telegram_link_expires_at", sa.DateTime(), nullable=True))
        if "telegram_linked_at" not in columns:
            batch_op.add_column(sa.Column("telegram_linked_at", sa.DateTime(), nullable=True))
        if "telegram_enabled" not in columns:
            batch_op.add_column(
                sa.Column("telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
            )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "delivery_drivers")

    if "ix_delivery_drivers_telegram_chat_id" not in indexes:
        op.create_index(
            "ix_delivery_drivers_telegram_chat_id",
            "delivery_drivers",
            ["telegram_chat_id"],
            unique=True,
        )
    if "ix_delivery_drivers_telegram_link_code" not in indexes:
        op.create_index(
            "ix_delivery_drivers_telegram_link_code",
            "delivery_drivers",
            ["telegram_link_code"],
            unique=False,
        )
    if "ix_delivery_drivers_telegram_link_expires_at" not in indexes:
        op.create_index(
            "ix_delivery_drivers_telegram_link_expires_at",
            "delivery_drivers",
            ["telegram_link_expires_at"],
            unique=False,
        )
    if "ix_delivery_drivers_telegram_linked_at" not in indexes:
        op.create_index(
            "ix_delivery_drivers_telegram_linked_at",
            "delivery_drivers",
            ["telegram_linked_at"],
            unique=False,
        )
    if "ix_delivery_drivers_telegram_enabled" not in indexes:
        op.create_index(
            "ix_delivery_drivers_telegram_enabled",
            "delivery_drivers",
            ["telegram_enabled"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "delivery_drivers")
    columns = _column_names(inspector, "delivery_drivers")

    for index_name in [
        "ix_delivery_drivers_telegram_enabled",
        "ix_delivery_drivers_telegram_linked_at",
        "ix_delivery_drivers_telegram_link_expires_at",
        "ix_delivery_drivers_telegram_link_code",
        "ix_delivery_drivers_telegram_chat_id",
    ]:
        if index_name in indexes:
            op.drop_index(index_name, table_name="delivery_drivers")

    with op.batch_alter_table("delivery_drivers") as batch_op:
        for column_name in [
            "telegram_enabled",
            "telegram_linked_at",
            "telegram_link_expires_at",
            "telegram_link_code",
            "telegram_username",
            "telegram_chat_id",
        ]:
            if column_name in columns:
                batch_op.drop_column(column_name)
