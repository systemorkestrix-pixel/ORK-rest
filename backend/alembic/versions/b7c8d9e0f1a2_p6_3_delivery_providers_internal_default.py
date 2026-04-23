"""p6_3 delivery providers internal default

Revision ID: b7c8d9e0f1a2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-28 22:10:00.000000
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op


revision = "b7c8d9e0f1a2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if "delivery_providers" not in inspector.get_table_names():
        op.create_table(
            "delivery_providers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("provider_type", sa.String(length=32), nullable=False, server_default="internal_team"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_internal_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_delivery_providers_id", "delivery_providers", ["id"], unique=False)
        op.create_index("ix_delivery_providers_name", "delivery_providers", ["name"], unique=True)
        op.create_index("ix_delivery_providers_provider_type", "delivery_providers", ["provider_type"], unique=False)
        op.create_index("ix_delivery_providers_active", "delivery_providers", ["active"], unique=False)
        op.create_index("ix_delivery_providers_is_internal_default", "delivery_providers", ["is_internal_default"], unique=False)
        op.create_index("ix_delivery_providers_created_at", "delivery_providers", ["created_at"], unique=False)
    else:
        provider_indexes = _index_names(inspector, "delivery_providers")
        if "ix_delivery_providers_id" not in provider_indexes:
            op.create_index("ix_delivery_providers_id", "delivery_providers", ["id"], unique=False)
        if "ix_delivery_providers_name" not in provider_indexes:
            op.create_index("ix_delivery_providers_name", "delivery_providers", ["name"], unique=True)
        if "ix_delivery_providers_provider_type" not in provider_indexes:
            op.create_index("ix_delivery_providers_provider_type", "delivery_providers", ["provider_type"], unique=False)
        if "ix_delivery_providers_active" not in provider_indexes:
            op.create_index("ix_delivery_providers_active", "delivery_providers", ["active"], unique=False)
        if "ix_delivery_providers_is_internal_default" not in provider_indexes:
            op.create_index("ix_delivery_providers_is_internal_default", "delivery_providers", ["is_internal_default"], unique=False)
        if "ix_delivery_providers_created_at" not in provider_indexes:
            op.create_index("ix_delivery_providers_created_at", "delivery_providers", ["created_at"], unique=False)

    driver_columns = {column["name"] for column in inspector.get_columns("delivery_drivers")}
    driver_indexes = _index_names(inspector, "delivery_drivers")
    if "provider_id" not in driver_columns:
        with op.batch_alter_table("delivery_drivers") as batch_op:
            batch_op.add_column(sa.Column("provider_id", sa.Integer(), nullable=True))
            batch_op.create_index("ix_delivery_drivers_provider_id", ["provider_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_delivery_drivers_provider_id_delivery_providers",
                "delivery_providers",
                ["provider_id"],
                ["id"],
            )
    elif "ix_delivery_drivers_provider_id" not in driver_indexes:
        op.create_index("ix_delivery_drivers_provider_id", "delivery_drivers", ["provider_id"], unique=False)

    provider_id = connection.execute(
        sa.text("SELECT id FROM delivery_providers WHERE is_internal_default = TRUE LIMIT 1")
    ).scalar_one_or_none()
    if provider_id is None:
        provider_id = connection.execute(
            sa.text(
                """
                INSERT INTO delivery_providers (name, provider_type, active, is_internal_default, created_at)
                VALUES (:name, :provider_type, :active, :is_internal_default, :created_at)
                RETURNING id
                """
            ),
            {
                "name": "الفريق الداخلي",
                "provider_type": "internal_team",
                "active": True,
                "is_internal_default": True,
                "created_at": datetime.now(UTC),
            },
        ).scalar_one()

    connection.execute(
        sa.text(
            """
            UPDATE delivery_providers
            SET name = :name, provider_type = :provider_type, active = :active
            WHERE id = :provider_id
            """
        ),
        {
            "name": "الفريق الداخلي",
            "provider_type": "internal_team",
            "active": True,
            "provider_id": int(provider_id),
        },
    )
    connection.execute(
        sa.text("UPDATE delivery_drivers SET provider_id = :provider_id WHERE provider_id IS NULL"),
        {"provider_id": int(provider_id)},
    )


def downgrade() -> None:
    with op.batch_alter_table("delivery_drivers") as batch_op:
        batch_op.drop_constraint("fk_delivery_drivers_provider_id_delivery_providers", type_="foreignkey")
        batch_op.drop_index("ix_delivery_drivers_provider_id")
        batch_op.drop_column("provider_id")

    op.drop_index("ix_delivery_providers_created_at", table_name="delivery_providers")
    op.drop_index("ix_delivery_providers_is_internal_default", table_name="delivery_providers")
    op.drop_index("ix_delivery_providers_active", table_name="delivery_providers")
    op.drop_index("ix_delivery_providers_provider_type", table_name="delivery_providers")
    op.drop_index("ix_delivery_providers_name", table_name="delivery_providers")
    op.drop_index("ix_delivery_providers_id", table_name="delivery_providers")
    op.drop_table("delivery_providers")
