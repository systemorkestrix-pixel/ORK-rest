"""p5_2_delivery_location_provider_cache

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-03-22 23:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("delivery_location_cache"):
        op.create_table(
            "delivery_location_cache",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("node_key", sa.String(length=160), nullable=False),
            sa.Column("parent_key", sa.String(length=160), nullable=True),
            sa.Column("level", sa.String(length=32), nullable=False),
            sa.Column("external_id", sa.String(length=64), nullable=True),
            sa.Column("country_code", sa.String(length=8), nullable=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("refreshed_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("node_key"),
        )
        with op.batch_alter_table("delivery_location_cache", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_id"), ["id"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_provider"), ["provider"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_node_key"), ["node_key"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_parent_key"), ["parent_key"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_level"), ["level"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_external_id"), ["external_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_country_code"), ["country_code"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_expires_at"), ["expires_at"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_refreshed_at"), ["refreshed_at"], unique=False)
            batch_op.create_index(batch_op.f("ix_delivery_location_cache_created_at"), ["created_at"], unique=False)
            batch_op.create_index(
                "ix_delivery_location_cache_provider_parent_level",
                ["provider", "parent_key", "level"],
                unique=False,
            )
            batch_op.create_index(
                "ix_delivery_location_cache_provider_expires_at",
                ["provider", "expires_at"],
                unique=False,
            )
            batch_op.create_index(
                "ix_delivery_location_cache_country_level",
                ["country_code", "level"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("delivery_location_cache"):
        with op.batch_alter_table("delivery_location_cache", schema=None) as batch_op:
            batch_op.drop_index("ix_delivery_location_cache_country_level")
            batch_op.drop_index("ix_delivery_location_cache_provider_expires_at")
            batch_op.drop_index("ix_delivery_location_cache_provider_parent_level")
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_created_at"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_refreshed_at"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_expires_at"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_country_code"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_external_id"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_level"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_parent_key"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_node_key"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_provider"))
            batch_op.drop_index(batch_op.f("ix_delivery_location_cache_id"))
        op.drop_table("delivery_location_cache")
