"""add delivery_zone_pricing

Revision ID: e60afb356e90
Revises: k0e1f2a3b4c5
Create Date: 2026-04-17 16:47:49.895833
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'e60afb356e90'
down_revision: Union[str, Sequence[str], None] = 'k0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Safe upgrade:
    - No destructive operations on uncertain legacy tables
    - Focus only on schema additions for delivery_zone_pricing
    """

    # =========================
    # 1. CORE FEATURE (SAFE ADD)
    # =========================

    op.create_table(
        'delivery_zone_pricing',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('zone_name', sa.String(length=100), nullable=False),
        sa.Column('base_fee', sa.Float(), nullable=False),
        sa.Column('per_km_fee', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # =========================
    # 2. OPTIONAL NON-CRITICAL CLEANUPS
    # =========================
    # Removed:
    # - drop_table(subscription_state) → unsafe across environments
    # - index drops → can break partial DB states
    # - bulk alters → should be separate migrations

    # If these changes are required, they must be moved
    # into dedicated guarded migrations later.


def downgrade() -> None:
    """
    Reverse only what this migration safely creates.
    """

    op.drop_table('delivery_zone_pricing')