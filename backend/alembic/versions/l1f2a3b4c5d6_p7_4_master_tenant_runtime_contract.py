"""p7.4 add master tenant runtime/migration contract

Revision ID: l1f2a3b4c5d6
Revises: k0e1f2a3b4c5
Create Date: 2026-04-23 21:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "l1f2a3b4c5d6"
down_revision = "k0e1f2a3b4c5"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "master_tenants" not in set(inspector.get_table_names()):
        return

    columns = _column_names(inspector, "master_tenants")
    indexes = _index_names(inspector, "master_tenants")

    with op.batch_alter_table("master_tenants") as batch_op:
        if "runtime_storage_backend" not in columns:
            batch_op.add_column(
                sa.Column("runtime_storage_backend", sa.String(length=32), nullable=False, server_default="sqlite_file")
            )
        if "runtime_schema_name" not in columns:
            batch_op.add_column(sa.Column("runtime_schema_name", sa.String(length=120), nullable=True))
        if "runtime_migration_state" not in columns:
            batch_op.add_column(
                sa.Column("runtime_migration_state", sa.String(length=32), nullable=False, server_default="not_started")
            )
        if "runtime_migrated_at" not in columns:
            batch_op.add_column(sa.Column("runtime_migrated_at", sa.DateTime(), nullable=True))
        if "media_storage_backend" not in columns:
            batch_op.add_column(
                sa.Column("media_storage_backend", sa.String(length=32), nullable=False, server_default="local_static")
            )

    if "ix_master_tenants_runtime_storage_backend" not in indexes:
        op.create_index(
            "ix_master_tenants_runtime_storage_backend",
            "master_tenants",
            ["runtime_storage_backend"],
            unique=False,
        )
    if "ix_master_tenants_runtime_migration_state" not in indexes:
        op.create_index(
            "ix_master_tenants_runtime_migration_state",
            "master_tenants",
            ["runtime_migration_state"],
            unique=False,
        )
    if "ix_master_tenants_media_storage_backend" not in indexes:
        op.create_index(
            "ix_master_tenants_media_storage_backend",
            "master_tenants",
            ["media_storage_backend"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "master_tenants" not in set(inspector.get_table_names()):
        return

    columns = _column_names(inspector, "master_tenants")
    indexes = _index_names(inspector, "master_tenants")

    if "ix_master_tenants_media_storage_backend" in indexes:
        op.drop_index("ix_master_tenants_media_storage_backend", table_name="master_tenants")
    if "ix_master_tenants_runtime_migration_state" in indexes:
        op.drop_index("ix_master_tenants_runtime_migration_state", table_name="master_tenants")
    if "ix_master_tenants_runtime_storage_backend" in indexes:
        op.drop_index("ix_master_tenants_runtime_storage_backend", table_name="master_tenants")

    with op.batch_alter_table("master_tenants") as batch_op:
        if "media_storage_backend" in columns:
            batch_op.drop_column("media_storage_backend")
        if "runtime_migrated_at" in columns:
            batch_op.drop_column("runtime_migrated_at")
        if "runtime_migration_state" in columns:
            batch_op.drop_column("runtime_migration_state")
        if "runtime_schema_name" in columns:
            batch_op.drop_column("runtime_schema_name")
        if "runtime_storage_backend" in columns:
            batch_op.drop_column("runtime_storage_backend")
