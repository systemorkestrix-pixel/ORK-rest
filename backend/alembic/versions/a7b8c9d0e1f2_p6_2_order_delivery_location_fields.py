"""p6_2_order_delivery_location_fields

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-24 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("orders")}

    with op.batch_alter_table("orders", schema=None) as batch_op:
        if "delivery_location_key" not in existing_columns:
            batch_op.add_column(sa.Column("delivery_location_key", sa.String(length=160), nullable=True))
        if "delivery_location_label" not in existing_columns:
            batch_op.add_column(sa.Column("delivery_location_label", sa.String(length=255), nullable=True))
        if "delivery_location_level" not in existing_columns:
            batch_op.add_column(sa.Column("delivery_location_level", sa.String(length=32), nullable=True))
        if "delivery_location_snapshot_json" not in existing_columns:
            batch_op.add_column(sa.Column("delivery_location_snapshot_json", sa.Text(), nullable=True))

        if "ix_orders_delivery_location_key" not in existing_indexes:
            batch_op.create_index("ix_orders_delivery_location_key", ["delivery_location_key"], unique=False)
        if "ix_orders_delivery_location_level" not in existing_indexes:
            batch_op.create_index("ix_orders_delivery_location_level", ["delivery_location_level"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    existing_indexes = {index["name"] for index in inspector.get_indexes("orders")}

    with op.batch_alter_table("orders", schema=None) as batch_op:
        if "ix_orders_delivery_location_level" in existing_indexes:
            batch_op.drop_index("ix_orders_delivery_location_level")
        if "ix_orders_delivery_location_key" in existing_indexes:
            batch_op.drop_index("ix_orders_delivery_location_key")

        if "delivery_location_snapshot_json" in existing_columns:
            batch_op.drop_column("delivery_location_snapshot_json")
        if "delivery_location_level" in existing_columns:
            batch_op.drop_column("delivery_location_level")
        if "delivery_location_label" in existing_columns:
            batch_op.drop_column("delivery_location_label")
        if "delivery_location_key" in existing_columns:
            batch_op.drop_column("delivery_location_key")
