"""Create base database

Revision ID: 0d992f099915
Revises: 
Create Date: 2021-06-19 22:11:47.344803

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d992f099915'
down_revision = None
branch_labels = None
depends_on = None

# this was all done by alembic --autogenerate, so don't sue me

def upgrade():
    op.create_table('backgrounds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=150, collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('description', sa.Text(collation='utf8mb4_unicode_ci'), nullable=True),
        sa.Column('image_url', sa.Text(length=500, collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('created_on', sa.TIMESTAMP(), nullable=True),
        sa.Column('usable_by_default', sa.Boolean(), nullable=False),
        sa.Column('hidden', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_backgrounds')),
        sa.UniqueConstraint('server_id', 'name', name=op.f('uq_backgrounds_server_id'))
    )
    op.create_index(op.f('ix_backgrounds_name'), 'backgrounds', ['name'], unique=False)
    op.create_index(op.f('ix_backgrounds_server_id'), 'backgrounds', ['server_id'], unique=False)

    op.create_table('badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255, collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('description', sa.Text(collation='utf8mb4_unicode_ci'), nullable=True),
        sa.Column('icon', sa.String(length=128, collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('created_on', sa.TIMESTAMP(), nullable=True),
        sa.Column('levels', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_badges'))
    )
    op.create_index(op.f('ix_badges_icon'), 'badges', ['icon'], unique=False)
    op.create_index(op.f('ix_badges_name'), 'badges', ['name'], unique=False)
    op.create_index(op.f('ix_badges_server_id'), 'badges', ['server_id'], unique=False)

    op.create_table('bot_options',
        sa.Column('option', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('option', name=op.f('pk_bot_options'))
    )

    op.create_table('server_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('data', sa.Text(collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('created_on', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_server_options'))
    )
    op.create_index(op.f('ix_server_options_server_id'), 'server_options', ['server_id'], unique=False)
    
    op.create_table('tags',
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=128, collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('content', sa.Text(collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('created_on', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('server_id', 'name', name=op.f('pk_tags'))
    )

    op.create_table('background_winners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('discord_id', sa.BigInteger(), nullable=False),
        sa.Column('background_id', sa.Integer(), nullable=False),
        sa.Column('awarded', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['background_id'], ['backgrounds.id'], name=op.f('fk_background_winners_background_id_backgrounds'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_background_winners')),
        sa.UniqueConstraint('discord_id', 'background_id', name=op.f('uq_background_winners_discord_id'))
    )
    op.create_index(op.f('ix_background_winners_discord_id'), 'background_winners', ['discord_id'], unique=False)
    op.create_index(op.f('ix_background_winners_server_id'), 'background_winners', ['server_id'], unique=False)
    
    op.create_table('badge_winners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('discord_id', sa.BigInteger(), nullable=False),
        sa.Column('badge_id', sa.Integer(), nullable=False),
        sa.Column('awarded', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['badge_id'], ['badges.id'], name=op.f('fk_badge_winners_badge_id_badges'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_badge_winners'))
    )
    op.create_index(op.f('ix_badge_winners_discord_id'), 'badge_winners', ['discord_id'], unique=False)
    op.create_index(op.f('ix_badge_winners_server_id'), 'badge_winners', ['server_id'], unique=False)
    
    op.create_table('profile_preferences',
        sa.Column('server_id', sa.BigInteger(), nullable=False),
        sa.Column('discord_id', sa.BigInteger(), nullable=False),
        sa.Column('spotlighted_award_id', sa.Integer(), nullable=True),
        sa.Column('background_award_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['background_award_id'], ['background_winners.id'], name=op.f('fk_profile_preferences_background_award_id_background_winners'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['spotlighted_award_id'], ['badge_winners.id'], name=op.f('fk_profile_preferences_spotlighted_award_id_badge_winners'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('server_id', 'discord_id', name=op.f('pk_profile_preferences'))
    )


def downgrade():
    op.drop_table('profile_preferences')

    op.drop_index(op.f('ix_badge_winners_server_id'), table_name='badge_winners')
    op.drop_index(op.f('ix_badge_winners_discord_id'), table_name='badge_winners')
    op.drop_table('badge_winners')

    op.drop_index(op.f('ix_background_winners_server_id'), table_name='background_winners')
    op.drop_index(op.f('ix_background_winners_discord_id'), table_name='background_winners')

    op.drop_table('background_winners')
    op.drop_table('tags')

    op.drop_index(op.f('ix_server_options_server_id'), table_name='server_options')
    op.drop_table('server_options')

    op.drop_table('bot_options')

    op.drop_index(op.f('ix_badges_server_id'), table_name='badges')
    op.drop_index(op.f('ix_badges_name'), table_name='badges')
    op.drop_index(op.f('ix_badges_icon'), table_name='badges')
    op.drop_table('badges')

    op.drop_index(op.f('ix_backgrounds_server_id'), table_name='backgrounds')
    op.drop_index(op.f('ix_backgrounds_name'), table_name='backgrounds')
    op.drop_table('backgrounds')
