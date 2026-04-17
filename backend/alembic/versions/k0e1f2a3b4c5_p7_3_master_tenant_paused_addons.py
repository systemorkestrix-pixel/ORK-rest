"""p7.3 add paused addons storage to master tenants

Revision ID: k0e1f2a3b4c5
Revises: j9d0e1f2a3b4
Create Date: 2026-04-16 13:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "k0e1f2a3b4c5"
down_revision = "j9d0e1f2a3b4"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "master_tenants" not in set(inspector.get_table_names()):
        return

    columns = _column_names(inspector, "master_tenants")
    if "paused_addons_json" not in columns:
        with op.batch_alter_table("master_tenants") as batch_op:
            batch_op.add_column(sa.Column("paused_addons_json", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "master_tenants" not in set(inspector.get_table_names()):
        return

    columns = _column_names(inspector, "master_tenants")
    if "paused_addons_json" in columns:
        with op.batch_alter_table("master_tenants") as batch_op:
            batch_op.drop_column("paused_addons_json")
