"""p6_1_manual_delivery_address_nodes

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-03-22 23:59:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("delivery_address_nodes"):
        op.create_table(
            "delivery_address_nodes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("level", sa.String(length=32), nullable=False),
            sa.Column("country_code", sa.String(length=8), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("postal_code", sa.String(length=32), nullable=True),
            sa.Column("notes", sa.String(length=255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("visible_in_public", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["parent_id"], ["delivery_address_nodes.id"]),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("parent_id", "code", name="uq_delivery_address_node_parent_code"),
        )
        with op.batch_alter_table("delivery_address_nodes", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_parent_id"), ["parent_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_level"), ["level"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_country_code"), ["country_code"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_active"), ["active"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_visible_in_public"), ["visible_in_public"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_created_at"), ["created_at"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_updated_at"), ["updated_at"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_address_nodes_updated_by"), ["updated_by"], unique=False)
            batch_op.create_index("ix_delivery_address_nodes_parent_sort", ["parent_id", "sort_order"], unique=False)
            batch_op.create_index("ix_delivery_address_nodes_country_level", ["country_code", "level"], unique=False)
            batch_op.create_index("ix_delivery_address_nodes_active_public", ["active", "visible_in_public"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("delivery_address_nodes"):
        with op.batch_alter_table("delivery_address_nodes", schema=None) as batch_op:
            batch_op.drop_index("ix_delivery_address_nodes_active_public")
            batch_op.drop_index("ix_delivery_address_nodes_country_level")
            batch_op.drop_index("ix_delivery_address_nodes_parent_sort")
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_updated_by"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_updated_at"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_created_at"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_visible_in_public"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_active"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_country_code"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_level"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_parent_id"))
            batch_op.drop_index(batch_op.f("ix_delivery_address_nodes_id"))
        op.drop_table("delivery_address_nodes")
