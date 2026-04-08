"""add daily_completed_on for manual daily check

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'curriculum_item',
        sa.Column('daily_completed_on', sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column('curriculum_item', 'daily_completed_on')
