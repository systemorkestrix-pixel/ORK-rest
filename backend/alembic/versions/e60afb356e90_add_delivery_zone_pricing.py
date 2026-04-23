"""add delivery_zone_pricing

Revision ID: e60afb356e90
Revises: k0e1f2a3b4c5
Create Date: 2026-04-17 16:47:49.895833
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e60afb356e90"
down_revision: Union[str, Sequence[str], None] = "k0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "delivery_zone_pricing"
UNIQUE_LOCATION_KEY = "uq_delivery_zone_pricing_location_key"
INDEX_PROVIDER_ACTIVE = "ix_delivery_zone_pricing_provider_active"
INDEX_COUNTRY_LEVEL = "ix_delivery_zone_pricing_country_level"
FK_UPDATED_BY = "fk_delivery_zone_pricing_updated_by_users"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name) if constraint.get("name")}


def _foreign_key_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}


def _create_indexes_and_constraints(inspector: sa.Inspector) -> None:
    index_names = _index_names(inspector, TABLE_NAME)
    unique_names = _unique_names(inspector, TABLE_NAME)
    fk_names = _foreign_key_names(inspector, TABLE_NAME)

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        if UNIQUE_LOCATION_KEY not in unique_names:
            batch_op.create_unique_constraint(UNIQUE_LOCATION_KEY, ["location_key"])
        if INDEX_PROVIDER_ACTIVE not in index_names:
            batch_op.create_index(INDEX_PROVIDER_ACTIVE, ["provider", "active"], unique=False)
        if INDEX_COUNTRY_LEVEL not in index_names:
            batch_op.create_index(INDEX_COUNTRY_LEVEL, ["country_code", "level"], unique=False)
        if FK_UPDATED_BY not in fk_names:
            batch_op.create_foreign_key(FK_UPDATED_BY, "users", ["updated_by"], ["id"])


def _create_full_table() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("location_key", sa.String(length=160), nullable=False),
        sa.Column("parent_key", sa.String(length=160), nullable=True),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("delivery_fee", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=FK_UPDATED_BY),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("location_key", name=UNIQUE_LOCATION_KEY),
    )
    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_provider"), ["provider"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_location_key"), ["location_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_parent_key"), ["parent_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_level"), ["level"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_external_id"), ["external_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_country_code"), ["country_code"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_active"), ["active"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_updated_at"), ["updated_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_zone_pricing_updated_by"), ["updated_by"], unique=False)
        batch_op.create_index(INDEX_PROVIDER_ACTIVE, ["provider", "active"], unique=False)
        batch_op.create_index(INDEX_COUNTRY_LEVEL, ["country_code", "level"], unique=False)


def upgrade() -> None:
    inspector = _inspector()
    if TABLE_NAME in _table_names(inspector):
        _create_indexes_and_constraints(inspector)
        return

    _create_full_table()


def downgrade() -> None:
    inspector = _inspector()
    if TABLE_NAME not in _table_names(inspector):
        return

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        for index_name in (
            INDEX_COUNTRY_LEVEL,
            INDEX_PROVIDER_ACTIVE,
            batch_op.f("ix_delivery_zone_pricing_updated_by"),
            batch_op.f("ix_delivery_zone_pricing_updated_at"),
            batch_op.f("ix_delivery_zone_pricing_created_at"),
            batch_op.f("ix_delivery_zone_pricing_active"),
            batch_op.f("ix_delivery_zone_pricing_country_code"),
            batch_op.f("ix_delivery_zone_pricing_external_id"),
            batch_op.f("ix_delivery_zone_pricing_level"),
            batch_op.f("ix_delivery_zone_pricing_parent_key"),
            batch_op.f("ix_delivery_zone_pricing_location_key"),
            batch_op.f("ix_delivery_zone_pricing_provider"),
            batch_op.f("ix_delivery_zone_pricing_id"),
        ):
            try:
                batch_op.drop_index(index_name)
            except Exception:
                pass
        try:
            batch_op.drop_constraint(FK_UPDATED_BY, type_="foreignkey")
        except Exception:
            pass
        try:
            batch_op.drop_constraint(UNIQUE_LOCATION_KEY, type_="unique")
        except Exception:
            pass

    op.drop_table(TABLE_NAME)
