"""Add projects and curriculum metadata

Revision ID: 842c9f4b9f4f
Revises: 44cd4e544546
Create Date: 2026-04-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '842c9f4b9f4f'
down_revision = '44cd4e544546'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('curriculum', sa.Column('project_id', sa.Integer(), nullable=True))
    op.add_column('curriculum', sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
    op.add_column('curriculum', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('curriculum', sa.Column('target_completion_date', sa.Date(), nullable=True))
    op.create_foreign_key('fk_curriculum_project', 'curriculum', 'project', ['project_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_curriculum_project', 'curriculum', type_='foreignkey')
    op.drop_column('curriculum', 'target_completion_date')
    op.drop_column('curriculum', 'start_date')
    op.drop_column('curriculum', 'status')
    op.drop_column('curriculum', 'project_id')
    op.drop_table('project')
