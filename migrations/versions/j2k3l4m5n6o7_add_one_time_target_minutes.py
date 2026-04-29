"""add one_time_target_minutes and backfill task targets

Revision ID: j2k3l4m5n6o7
Revises: h1b2c3d4e5f6
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = 'j2k3l4m5n6o7'
down_revision = 'h1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('curriculum_item', sa.Column('one_time_target_minutes', sa.Integer(), nullable=True))

    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'sqlite':
        conn.execute(text(
            """
            UPDATE curriculum_item
            SET daily_target_minutes = CASE
                WHEN daily_target_minutes IS NOT NULL AND daily_target_minutes > 0 THEN daily_target_minutes
                WHEN hours_target IS NOT NULL AND hours_target > 0 THEN CAST(ROUND(hours_target * 60.0) AS INTEGER)
                ELSE 30
            END
            WHERE item_kind = 'daily'
            """
        ))
        conn.execute(text(
            """
            UPDATE curriculum_item
            SET completion_style = 'time_threshold'
            WHERE item_kind = 'daily'
            """
        ))
        conn.execute(text(
            """
            UPDATE curriculum_item
            SET one_time_target_minutes = CASE
                WHEN one_time_target_minutes IS NOT NULL AND one_time_target_minutes > 0 THEN one_time_target_minutes
                WHEN hours_target IS NOT NULL AND hours_target > 0 THEN CAST(ROUND(hours_target * 60.0) AS INTEGER)
                ELSE 60
            END
            WHERE item_kind = 'one_shot'
            """
        ))
    else:
        conn.execute(text(
            """
            UPDATE curriculum_item
            SET daily_target_minutes = CASE
                WHEN daily_target_minutes IS NOT NULL AND daily_target_minutes > 0 THEN daily_target_minutes
                WHEN hours_target IS NOT NULL AND hours_target > 0 THEN ROUND(hours_target * 60.0)::int
                ELSE 30
            END
            WHERE item_kind = 'daily'
            """
        ))
        conn.execute(text(
            """
            UPDATE curriculum_item
            SET completion_style = 'time_threshold'
            WHERE item_kind = 'daily'
            """
        ))
        conn.execute(text(
            """
            UPDATE curriculum_item
            SET one_time_target_minutes = CASE
                WHEN one_time_target_minutes IS NOT NULL AND one_time_target_minutes > 0 THEN one_time_target_minutes
                WHEN hours_target IS NOT NULL AND hours_target > 0 THEN ROUND(hours_target * 60.0)::int
                ELSE 60
            END
            WHERE item_kind = 'one_shot'
            """
        ))


def downgrade():
    op.drop_column('curriculum_item', 'one_time_target_minutes')
