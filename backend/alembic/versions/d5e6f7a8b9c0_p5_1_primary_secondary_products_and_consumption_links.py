"""p5_1_primary_secondary_products_and_consumption_links

Revision ID: d5e6f7a8b9c0
Revises: b4c2d7e9f0a1
Create Date: 2026-03-20 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "b4c2d7e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute(
        """
        UPDATE products
        SET kind = CASE LOWER(kind)
            WHEN 'sellable' THEN 'primary'
            WHEN 'primary' THEN 'primary'
            WHEN 'internal' THEN 'secondary'
            WHEN 'secondary' THEN 'secondary'
            ELSE 'primary'
        END
        """
    )

    if not inspector.has_table("product_secondary_links"):
        op.create_table(
            "product_secondary_links",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("primary_product_id", sa.Integer(), nullable=False),
            sa.Column("secondary_product_id", sa.Integer(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("max_quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("primary_product_id <> secondary_product_id", name="ck_product_secondary_link_not_self"),
            sa.CheckConstraint("max_quantity >= 1", name="ck_product_secondary_link_max_quantity"),
            sa.ForeignKeyConstraint(["primary_product_id"], ["products.id"]),
            sa.ForeignKeyConstraint(["secondary_product_id"], ["products.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("primary_product_id", "secondary_product_id", name="uq_product_secondary_link"),
        )
        with op.batch_alter_table("product_secondary_links", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_product_secondary_links_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_secondary_links_primary_product_id"), ["primary_product_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_secondary_links_secondary_product_id"), ["secondary_product_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_secondary_links_sort_order"), ["sort_order"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_secondary_links_is_default"), ["is_default"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_secondary_links_created_at"), ["created_at"], unique=False)

    if not inspector.has_table("product_consumption_components"):
        op.create_table(
            "product_consumption_components",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("warehouse_item_id", sa.Integer(), nullable=False),
            sa.Column("quantity_per_unit", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("quantity_per_unit > 0", name="ck_product_consumption_quantity"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.ForeignKeyConstraint(["warehouse_item_id"], ["wh_items.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("product_id", "warehouse_item_id", name="uq_product_consumption_component"),
        )
        with op.batch_alter_table("product_consumption_components", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_product_consumption_components_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_consumption_components_product_id"), ["product_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_consumption_components_warehouse_item_id"), ["warehouse_item_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_product_consumption_components_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("product_consumption_components"):
        with op.batch_alter_table("product_consumption_components", schema=None) as batch_op:
            batch_op.drop_index(batch_op.f("ix_product_consumption_components_created_at"))
            batch_op.drop_index(batch_op.f("ix_product_consumption_components_warehouse_item_id"))
            batch_op.drop_index(batch_op.f("ix_product_consumption_components_product_id"))
            batch_op.drop_index(batch_op.f("ix_product_consumption_components_id"))
        op.drop_table("product_consumption_components")

    if inspector.has_table("product_secondary_links"):
        with op.batch_alter_table("product_secondary_links", schema=None) as batch_op:
            batch_op.drop_index(batch_op.f("ix_product_secondary_links_created_at"))
            batch_op.drop_index(batch_op.f("ix_product_secondary_links_is_default"))
            batch_op.drop_index(batch_op.f("ix_product_secondary_links_sort_order"))
            batch_op.drop_index(batch_op.f("ix_product_secondary_links_secondary_product_id"))
            batch_op.drop_index(batch_op.f("ix_product_secondary_links_primary_product_id"))
            batch_op.drop_index(batch_op.f("ix_product_secondary_links_id"))
        op.drop_table("product_secondary_links")

    op.execute(
        """
        UPDATE products
        SET kind = CASE LOWER(kind)
            WHEN 'primary' THEN 'sellable'
            WHEN 'secondary' THEN 'internal'
            WHEN 'sellable' THEN 'sellable'
            WHEN 'internal' THEN 'internal'
            ELSE 'sellable'
        END
        """
    )
