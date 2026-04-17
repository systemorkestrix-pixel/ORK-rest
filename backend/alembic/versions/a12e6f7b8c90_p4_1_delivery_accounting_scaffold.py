"""p4_1_delivery_accounting_scaffold

Revision ID: a12e6f7b8c90
Revises: f1d2c3b4a5e6
Create Date: 2026-03-09 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a12e6f7b8c90"
down_revision: Union[str, Sequence[str], None] = "f1d2c3b4a5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("collected_by_channel", sa.String(length=24), nullable=False, server_default="cashier")
        )
        batch_op.add_column(
            sa.Column("collection_variance_amount", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("collection_variance_reason", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("accounting_recognized_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_orders_collected_by_channel", ["collected_by_channel"], unique=False)
        batch_op.create_index("ix_orders_accounting_recognized_at", ["accounting_recognized_at"], unique=False)

    op.create_table(
        "delivery_settlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("driver_share_model", sa.String(length=24), nullable=False, server_default="full_delivery_fee"),
        sa.Column("driver_share_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expected_customer_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_collected_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("food_revenue_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("delivery_revenue_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("driver_due_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("store_due_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("remitted_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("remaining_store_due_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("variance_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("variance_reason", sa.String(length=64), nullable=True),
        sa.Column("recognized_at", sa.DateTime(), nullable=False),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.Column("settled_by", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["delivery_assignments.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["delivery_drivers.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["settled_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_delivery_settlements_order_id"),
    )
    with op.batch_alter_table("delivery_settlements", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_delivery_settlements_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_settlements_order_id"), ["order_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_settlements_assignment_id"), ["assignment_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_settlements_driver_id"), ["driver_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_settlements_status"), ["status"], unique=False)
        batch_op.create_index("ix_delivery_settlements_driver_status", ["driver_id", "status"], unique=False)
        batch_op.create_index("ix_delivery_settlements_recognized_at", ["recognized_at"], unique=False)
        batch_op.create_index("ix_delivery_settlements_settled_at", ["settled_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_delivery_settlements_settled_by"), ["settled_by"], unique=False)

    with op.batch_alter_table("financial_transactions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("delivery_settlement_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("direction", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("account_code", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("reference_group", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_financial_transactions_delivery_settlement_id",
            "delivery_settlements",
            ["delivery_settlement_id"],
            ["id"],
        )
        batch_op.create_index(batch_op.f("ix_financial_transactions_delivery_settlement_id"), ["delivery_settlement_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_financial_transactions_direction"), ["direction"], unique=False)
        batch_op.create_index(batch_op.f("ix_financial_transactions_account_code"), ["account_code"], unique=False)
        batch_op.create_index("ix_financial_transactions_reference_group", ["reference_group"], unique=False)
        batch_op.create_index(
            "ix_financial_transactions_order_type_created_at",
            ["order_id", "type", "created_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_financial_transactions_settlement_type",
            ["delivery_settlement_id", "type"],
            unique=False,
        )

    op.create_table(
        "cashbox_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("delivery_settlement_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="driver_remittance"),
        sa.Column("direction", sa.String(length=8), nullable=False, server_default="in"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("cash_channel", sa.String(length=24), nullable=False, server_default="cash_drawer"),
        sa.Column("performed_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["delivery_settlement_id"], ["delivery_settlements.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("cashbox_movements", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_cashbox_movements_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_cashbox_movements_delivery_settlement_id"), ["delivery_settlement_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_cashbox_movements_order_id"), ["order_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_cashbox_movements_type"), ["type"], unique=False)
        batch_op.create_index(batch_op.f("ix_cashbox_movements_direction"), ["direction"], unique=False)
        batch_op.create_index(batch_op.f("ix_cashbox_movements_cash_channel"), ["cash_channel"], unique=False)
        batch_op.create_index(batch_op.f("ix_cashbox_movements_performed_by"), ["performed_by"], unique=False)
        batch_op.create_index(batch_op.f("ix_cashbox_movements_created_at"), ["created_at"], unique=False)
        batch_op.create_index("ix_cashbox_movements_type_created_at", ["type", "created_at"], unique=False)
        batch_op.create_index("ix_cashbox_movements_direction_created_at", ["direction", "created_at"], unique=False)
        batch_op.create_index(
            "ix_cashbox_movements_settlement_created_at",
            ["delivery_settlement_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("cashbox_movements", schema=None) as batch_op:
        batch_op.drop_index("ix_cashbox_movements_settlement_created_at")
        batch_op.drop_index("ix_cashbox_movements_direction_created_at")
        batch_op.drop_index("ix_cashbox_movements_type_created_at")
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_created_at"))
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_performed_by"))
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_cash_channel"))
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_direction"))
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_type"))
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_order_id"))
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_delivery_settlement_id"))
        batch_op.drop_index(batch_op.f("ix_cashbox_movements_id"))
    op.drop_table("cashbox_movements")

    with op.batch_alter_table("financial_transactions", schema=None) as batch_op:
        batch_op.drop_index("ix_financial_transactions_settlement_type")
        batch_op.drop_index("ix_financial_transactions_order_type_created_at")
        batch_op.drop_index("ix_financial_transactions_reference_group")
        batch_op.drop_index(batch_op.f("ix_financial_transactions_account_code"))
        batch_op.drop_index(batch_op.f("ix_financial_transactions_direction"))
        batch_op.drop_index(batch_op.f("ix_financial_transactions_delivery_settlement_id"))
        batch_op.drop_constraint("fk_financial_transactions_delivery_settlement_id", type_="foreignkey")
        batch_op.drop_column("reference_group")
        batch_op.drop_column("account_code")
        batch_op.drop_column("direction")
        batch_op.drop_column("delivery_settlement_id")

    with op.batch_alter_table("delivery_settlements", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_delivery_settlements_settled_by"))
        batch_op.drop_index("ix_delivery_settlements_settled_at")
        batch_op.drop_index("ix_delivery_settlements_recognized_at")
        batch_op.drop_index("ix_delivery_settlements_driver_status")
        batch_op.drop_index(batch_op.f("ix_delivery_settlements_status"))
        batch_op.drop_index(batch_op.f("ix_delivery_settlements_driver_id"))
        batch_op.drop_index(batch_op.f("ix_delivery_settlements_assignment_id"))
        batch_op.drop_index(batch_op.f("ix_delivery_settlements_order_id"))
        batch_op.drop_index(batch_op.f("ix_delivery_settlements_id"))
    op.drop_table("delivery_settlements")

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_index("ix_orders_accounting_recognized_at")
        batch_op.drop_index("ix_orders_collected_by_channel")
        batch_op.drop_column("accounting_recognized_at")
        batch_op.drop_column("collection_variance_reason")
        batch_op.drop_column("collection_variance_amount")
        batch_op.drop_column("collected_by_channel")
