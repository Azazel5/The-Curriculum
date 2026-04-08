"""add curriculum_item item_kind

Revision ID: c1d2e3f4a5b6
Revises: 842c9f4b9f4f
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = '842c9f4b9f4f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'curriculum_item',
        sa.Column('item_kind', sa.String(length=20), nullable=False, server_default='one_shot'),
    )


def downgrade():
    op.drop_column('curriculum_item', 'item_kind')
