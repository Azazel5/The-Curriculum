"""add completion_style and daily_target_minutes to curriculum_item

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'curriculum_item',
        sa.Column(
            'completion_style',
            sa.String(length=20),
            nullable=False,
            server_default='presence',
        ),
    )
    op.add_column(
        'curriculum_item',
        sa.Column('daily_target_minutes', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column('curriculum_item', 'daily_target_minutes')
    op.drop_column('curriculum_item', 'completion_style')
