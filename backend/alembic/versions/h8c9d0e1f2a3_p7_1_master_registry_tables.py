"""p7.1 add master registry tables

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-04-07 19:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "h8c9d0e1f2a3"
down_revision = "g7b8c9d0e1f2"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "master_clients" not in tables:
        op.create_table(
            "master_clients",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_name", sa.String(length=120), nullable=False),
            sa.Column("brand_name", sa.String(length=120), nullable=False),
            sa.Column("phone", sa.String(length=40), nullable=False),
            sa.Column("city", sa.String(length=120), nullable=False),
            sa.Column("active_plan_id", sa.String(length=40), nullable=False, server_default="base"),
            sa.Column("subscription_state", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("next_billing_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    inspector = sa.inspect(bind)
    client_indexes = _index_names(inspector, "master_clients")
    if "ix_master_clients_brand_name" not in client_indexes:
        op.create_index("ix_master_clients_brand_name", "master_clients", ["brand_name"], unique=False)
    if "ix_master_clients_active_plan_id" not in client_indexes:
        op.create_index("ix_master_clients_active_plan_id", "master_clients", ["active_plan_id"], unique=False)
    if "ix_master_clients_subscription_state" not in client_indexes:
        op.create_index("ix_master_clients_subscription_state", "master_clients", ["subscription_state"], unique=False)
    if "ix_master_clients_created_at" not in client_indexes:
        op.create_index("ix_master_clients_created_at", "master_clients", ["created_at"], unique=False)

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)
    if "master_tenants" not in tables:
        op.create_table(
            "master_tenants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("client_id", sa.Integer(), sa.ForeignKey("master_clients.id"), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("brand_name", sa.String(length=120), nullable=False),
            sa.Column("database_name", sa.String(length=120), nullable=False),
            sa.Column("manager_username", sa.String(length=120), nullable=False),
            sa.Column("environment_state", sa.String(length=24), nullable=False, server_default="pending_activation"),
            sa.Column("plan_id", sa.String(length=40), nullable=False, server_default="base"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    inspector = sa.inspect(bind)
    tenant_indexes = _index_names(inspector, "master_tenants")
    if "ix_master_tenants_client_id" not in tenant_indexes:
        op.create_index("ix_master_tenants_client_id", "master_tenants", ["client_id"], unique=False)
    if "ix_master_tenants_code" not in tenant_indexes:
        op.create_index("ix_master_tenants_code", "master_tenants", ["code"], unique=True)
    if "ix_master_tenants_brand_name" not in tenant_indexes:
        op.create_index("ix_master_tenants_brand_name", "master_tenants", ["brand_name"], unique=False)
    if "ix_master_tenants_database_name" not in tenant_indexes:
        op.create_index("ix_master_tenants_database_name", "master_tenants", ["database_name"], unique=True)
    if "ix_master_tenants_manager_username" not in tenant_indexes:
        op.create_index("ix_master_tenants_manager_username", "master_tenants", ["manager_username"], unique=True)
    if "ix_master_tenants_environment_state" not in tenant_indexes:
        op.create_index("ix_master_tenants_environment_state", "master_tenants", ["environment_state"], unique=False)
    if "ix_master_tenants_plan_id" not in tenant_indexes:
        op.create_index("ix_master_tenants_plan_id", "master_tenants", ["plan_id"], unique=False)
    if "ix_master_tenants_created_at" not in tenant_indexes:
        op.create_index("ix_master_tenants_created_at", "master_tenants", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_master_tenants_created_at", table_name="master_tenants")
    op.drop_index("ix_master_tenants_plan_id", table_name="master_tenants")
    op.drop_index("ix_master_tenants_environment_state", table_name="master_tenants")
    op.drop_index("ix_master_tenants_manager_username", table_name="master_tenants")
    op.drop_index("ix_master_tenants_database_name", table_name="master_tenants")
    op.drop_index("ix_master_tenants_brand_name", table_name="master_tenants")
    op.drop_index("ix_master_tenants_code", table_name="master_tenants")
    op.drop_index("ix_master_tenants_client_id", table_name="master_tenants")
    op.drop_table("master_tenants")

    op.drop_index("ix_master_clients_created_at", table_name="master_clients")
    op.drop_index("ix_master_clients_subscription_state", table_name="master_clients")
    op.drop_index("ix_master_clients_active_plan_id", table_name="master_clients")
    op.drop_index("ix_master_clients_brand_name", table_name="master_clients")
    op.drop_table("master_clients")
