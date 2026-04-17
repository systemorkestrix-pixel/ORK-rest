"""p7.2 add restaurant staff directory

Revision ID: j9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-04-08 19:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "j9d0e1f2a3b4"
down_revision = "h8c9d0e1f2a3"
branch_labels = None
depends_on = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "restaurant_employees" not in _table_names(inspector):
        op.create_table(
            "restaurant_employees",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("employee_type", sa.String(length=40), nullable=False),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column("compensation_cycle", sa.String(length=20), nullable=False, server_default="monthly"),
            sa.Column("compensation_amount", sa.Float(), nullable=False, server_default="0"),
            sa.Column("work_schedule", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    inspector = sa.inspect(bind)
    indexes = _index_names(inspector, "restaurant_employees")
    if "ix_restaurant_employees_name" not in indexes:
        op.create_index("ix_restaurant_employees_name", "restaurant_employees", ["name"], unique=False)
    if "ix_restaurant_employees_employee_type" not in indexes:
        op.create_index("ix_restaurant_employees_employee_type", "restaurant_employees", ["employee_type"], unique=False)
    if "ix_restaurant_employees_active" not in indexes:
        op.create_index("ix_restaurant_employees_active", "restaurant_employees", ["active"], unique=False)
    if "ix_restaurant_employees_created_at" not in indexes:
        op.create_index("ix_restaurant_employees_created_at", "restaurant_employees", ["created_at"], unique=False)
    if "ix_restaurant_employees_type_active" not in indexes:
        op.create_index(
            "ix_restaurant_employees_type_active",
            "restaurant_employees",
            ["employee_type", "active"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_restaurant_employees_type_active", table_name="restaurant_employees")
    op.drop_index("ix_restaurant_employees_created_at", table_name="restaurant_employees")
    op.drop_index("ix_restaurant_employees_active", table_name="restaurant_employees")
    op.drop_index("ix_restaurant_employees_employee_type", table_name="restaurant_employees")
    op.drop_index("ix_restaurant_employees_name", table_name="restaurant_employees")
    op.drop_table("restaurant_employees")
