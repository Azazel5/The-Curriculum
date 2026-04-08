"""add app_user and user_id scoping

Revision ID: h1b2c3d4e5f6
Revises: g7h8i9j0k1l2
Create Date: 2026-04-08

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect


# revision identifiers, used by Alembic.
revision = 'h1b2c3d4e5f6'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    inspector = inspect(conn)

    if not inspector.has_table('app_user'):
        op.create_table(
            'app_user',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('email', sa.String(length=255), nullable=True),
            sa.Column('password_hash', sa.String(length=255), nullable=True),
            sa.Column('is_guest', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('email', name='uq_app_user_email'),
        )

    # Insert a default owner user so existing data can be claimed.
    # We pin id=1 for a deterministic backfill.
    if dialect == 'sqlite':
        conn.execute(text("INSERT OR IGNORE INTO app_user (id, email, password_hash, is_guest, created_at) VALUES (1, NULL, NULL, 0, CURRENT_TIMESTAMP)"))
    else:
        conn.execute(text("INSERT INTO app_user (id, email, password_hash, is_guest, created_at) VALUES (1, NULL, NULL, false, CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING"))
        # Ensure sequence is at least 1 after explicit insert
        conn.execute(text("SELECT setval(pg_get_serial_sequence('app_user','id'), (SELECT MAX(id) FROM app_user))"))

    if dialect == 'sqlite':
        with op.batch_alter_table('project', recreate='always') as batch:
            batch.add_column(sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))
            batch.create_index('ix_project_user_id', ['user_id'], unique=False)
            batch.create_foreign_key('fk_project_user_id', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')

        with op.batch_alter_table('curriculum', recreate='always') as batch:
            batch.add_column(sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))
            batch.create_index('ix_curriculum_user_id', ['user_id'], unique=False)
            batch.create_foreign_key('fk_curriculum_user_id', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')

        with op.batch_alter_table('settings', recreate='always') as batch:
            batch.add_column(sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))
            batch.create_index('ix_settings_user_id', ['user_id'], unique=False)
            batch.create_foreign_key('fk_settings_user_id', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')
            batch.create_unique_constraint('uq_settings_user_id', ['user_id'])

        # Ensure any existing rows are set (server_default handles new column values; this is extra safety)
        conn.execute(text("UPDATE project SET user_id = 1 WHERE user_id IS NULL"))
        conn.execute(text("UPDATE curriculum SET user_id = 1 WHERE user_id IS NULL"))
        conn.execute(text("UPDATE settings SET user_id = 1 WHERE user_id IS NULL"))
    else:
        op.add_column('project', sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_index('ix_project_user_id', 'project', ['user_id'], unique=False)
        op.create_foreign_key('fk_project_user_id', 'project', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')

        op.add_column('curriculum', sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_index('ix_curriculum_user_id', 'curriculum', ['user_id'], unique=False)
        op.create_foreign_key('fk_curriculum_user_id', 'curriculum', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')

        op.add_column('settings', sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_index('ix_settings_user_id', 'settings', ['user_id'], unique=False)
        op.create_foreign_key('fk_settings_user_id', 'settings', 'app_user', ['user_id'], ['id'], ondelete='CASCADE')

        conn.execute(text("UPDATE project SET user_id = 1 WHERE user_id IS NULL"))
        conn.execute(text("UPDATE curriculum SET user_id = 1 WHERE user_id IS NULL"))
        conn.execute(text("UPDATE settings SET user_id = 1 WHERE user_id IS NULL"))

        op.alter_column('project', 'user_id', existing_type=sa.Integer(), nullable=False)
        op.alter_column('curriculum', 'user_id', existing_type=sa.Integer(), nullable=False)
        op.alter_column('settings', 'user_id', existing_type=sa.Integer(), nullable=False)

        op.create_unique_constraint('uq_settings_user_id', 'settings', ['user_id'])


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == 'sqlite':
        with op.batch_alter_table('settings', recreate='always') as batch:
            batch.drop_constraint('uq_settings_user_id', type_='unique')
            batch.drop_constraint('fk_settings_user_id', type_='foreignkey')
            batch.drop_index('ix_settings_user_id')
            batch.drop_column('user_id')

        with op.batch_alter_table('curriculum', recreate='always') as batch:
            batch.drop_constraint('fk_curriculum_user_id', type_='foreignkey')
            batch.drop_index('ix_curriculum_user_id')
            batch.drop_column('user_id')

        with op.batch_alter_table('project', recreate='always') as batch:
            batch.drop_constraint('fk_project_user_id', type_='foreignkey')
            batch.drop_index('ix_project_user_id')
            batch.drop_column('user_id')
    else:
        op.drop_constraint('uq_settings_user_id', 'settings', type_='unique')

        op.drop_constraint('fk_settings_user_id', 'settings', type_='foreignkey')
        op.drop_index('ix_settings_user_id', table_name='settings')
        op.drop_column('settings', 'user_id')

        op.drop_constraint('fk_curriculum_user_id', 'curriculum', type_='foreignkey')
        op.drop_index('ix_curriculum_user_id', table_name='curriculum')
        op.drop_column('curriculum', 'user_id')

        op.drop_constraint('fk_project_user_id', 'project', type_='foreignkey')
        op.drop_index('ix_project_user_id', table_name='project')
        op.drop_column('project', 'user_id')

    op.drop_table('app_user')

