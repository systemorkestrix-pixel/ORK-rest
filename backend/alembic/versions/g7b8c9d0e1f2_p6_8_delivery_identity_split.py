"""p6.8 split delivery provider account from driver login

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-31 00:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "g7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    provider_columns = _column_names(inspector, "delivery_providers")
    if "account_user_id" not in provider_columns:
        with op.batch_alter_table("delivery_providers") as batch_op:
            batch_op.add_column(sa.Column("account_user_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_delivery_providers_account_user_id_users",
                "users",
                ["account_user_id"],
                ["id"],
            )

    inspector = sa.inspect(bind)
    provider_indexes = _index_names(inspector, "delivery_providers")
    if "ix_delivery_providers_account_user_id" not in provider_indexes:
        op.create_index(
            "ix_delivery_providers_account_user_id",
            "delivery_providers",
            ["account_user_id"],
            unique=True,
        )

    with op.batch_alter_table("delivery_drivers") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    provider_indexes = _index_names(inspector, "delivery_providers")
    if "ix_delivery_providers_account_user_id" in provider_indexes:
        op.drop_index("ix_delivery_providers_account_user_id", table_name="delivery_providers")

    provider_columns = _column_names(inspector, "delivery_providers")
    if "account_user_id" in provider_columns:
        with op.batch_alter_table("delivery_providers") as batch_op:
            batch_op.drop_column("account_user_id")

    with op.batch_alter_table("delivery_drivers") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
