"""add item_activity_day for daily presence history (heatmap / streak)

Revision ID: g7h8i9j0k1l2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'g7h8i9j0k1l2'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'item_activity_day',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('activity_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['curriculum_item.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id', 'activity_date', name='uq_item_activity_day'),
    )
    op.create_index('ix_item_activity_day_activity_date', 'item_activity_day', ['activity_date'], unique=False)

    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == 'sqlite':
        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO item_activity_day (item_id, activity_date, created_at)
                SELECT id, daily_completed_on, CURRENT_TIMESTAMP
                FROM curriculum_item
                WHERE deleted = 0
                  AND item_kind = 'daily'
                  AND completion_style = 'presence'
                  AND daily_completed_on IS NOT NULL
                """
            )
        )
    else:
        conn.execute(
            text(
                """
                INSERT INTO item_activity_day (item_id, activity_date, created_at)
                SELECT id, daily_completed_on, CURRENT_TIMESTAMP
                FROM curriculum_item
                WHERE deleted IS false
                  AND item_kind = 'daily'
                  AND completion_style = 'presence'
                  AND daily_completed_on IS NOT NULL
                ON CONFLICT (item_id, activity_date) DO NOTHING
                """
            )
        )


def downgrade():
    op.drop_index('ix_item_activity_day_activity_date', table_name='item_activity_day')
    op.drop_table('item_activity_day')
