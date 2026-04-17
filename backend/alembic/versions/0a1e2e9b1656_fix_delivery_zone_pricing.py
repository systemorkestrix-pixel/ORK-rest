"""fix delivery_zone_pricing

Revision ID: 0a1e2e9b1656
Revises: e60afb356e90
Create Date: 2026-04-17 17:06:25.752025
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0a1e2e9b1656"
down_revision: Union[str, Sequence[str], None] = "e60afb356e90"
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


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name) if constraint.get("name")}


def _foreign_key_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}


def _ensure_column(column_names: set[str], column: sa.Column) -> None:
    if column.name in column_names:
        return
    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.add_column(column)
    column_names.add(str(column.name))


def _create_missing_indexes_and_constraints(inspector: sa.Inspector) -> None:
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


def upgrade() -> None:
    inspector = _inspector()
    if TABLE_NAME not in _table_names(inspector):
        return

    columns = _column_names(inspector, TABLE_NAME)
    _ensure_column(columns, sa.Column("provider", sa.String(length=32), nullable=True))
    _ensure_column(columns, sa.Column("location_key", sa.String(length=160), nullable=True))
    _ensure_column(columns, sa.Column("parent_key", sa.String(length=160), nullable=True))
    _ensure_column(columns, sa.Column("level", sa.String(length=32), nullable=True))
    _ensure_column(columns, sa.Column("external_id", sa.String(length=64), nullable=True))
    _ensure_column(columns, sa.Column("country_code", sa.String(length=8), nullable=True))
    _ensure_column(columns, sa.Column("name", sa.String(length=160), nullable=True))
    _ensure_column(columns, sa.Column("display_name", sa.String(length=255), nullable=True))
    _ensure_column(columns, sa.Column("delivery_fee", sa.Float(), nullable=True))
    _ensure_column(columns, sa.Column("active", sa.Boolean(), nullable=True))
    _ensure_column(columns, sa.Column("sort_order", sa.Integer(), nullable=True))
    _ensure_column(columns, sa.Column("updated_at", sa.DateTime(), nullable=True))
    _ensure_column(columns, sa.Column("updated_by", sa.Integer(), nullable=True))

    connection = op.get_bind()

    connection.execute(
        sa.text(
            f"""
            UPDATE {TABLE_NAME}
            SET provider = COALESCE(NULLIF(provider, ''), 'manual')
            WHERE provider IS NULL OR provider = ''
            """
        )
    )
    connection.execute(
        sa.text(
            f"""
            UPDATE {TABLE_NAME}
            SET location_key = COALESCE(location_key, 'legacy-zone-' || CAST(id AS TEXT))
            WHERE location_key IS NULL
            """
        )
    )
    if "zone_name" in columns:
        connection.execute(
            sa.text(
                f"""
                UPDATE {TABLE_NAME}
                SET name = COALESCE(name, zone_name),
                    display_name = COALESCE(display_name, zone_name)
                WHERE name IS NULL OR display_name IS NULL
                """
            )
        )
    connection.execute(
        sa.text(
            f"""
            UPDATE {TABLE_NAME}
            SET name = COALESCE(name, location_key),
                display_name = COALESCE(display_name, name, location_key),
                level = COALESCE(level, 'zone'),
                sort_order = COALESCE(sort_order, 0),
                created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
                updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            WHERE name IS NULL
               OR display_name IS NULL
               OR level IS NULL
               OR sort_order IS NULL
               OR created_at IS NULL
               OR updated_at IS NULL
            """
        )
    )
    if "base_fee" in columns:
        connection.execute(
            sa.text(
                f"""
                UPDATE {TABLE_NAME}
                SET delivery_fee = COALESCE(delivery_fee, base_fee, 0)
                WHERE delivery_fee IS NULL
                """
            )
        )
    else:
        connection.execute(
            sa.text(
                f"""
                UPDATE {TABLE_NAME}
                SET delivery_fee = 0
                WHERE delivery_fee IS NULL
                """
            )
        )
    if "is_active" in columns:
        connection.execute(
            sa.text(
                f"""
                UPDATE {TABLE_NAME}
                SET active = COALESCE(active, is_active, 1)
                WHERE active IS NULL
                """
            )
        )
    else:
        connection.execute(
            sa.text(
                f"""
                UPDATE {TABLE_NAME}
                SET active = 1
                WHERE active IS NULL
                """
            )
        )

    inspector = _inspector()
    _create_missing_indexes_and_constraints(inspector)


def downgrade() -> None:
    """No-op downgrade.

    This revision repairs historical delivery pricing schemas in place.
    Rolling it back automatically would risk data loss on live environments.
    """

    return None
