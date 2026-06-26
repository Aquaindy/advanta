"""suggested_copies: Growth Content Studio artifacts

Adds the `suggested_copies` table — ready-to-use copy (keyword plans, ad copy,
landing-page copy, lifecycle emails, social hooks, SEO meta tags) the Growth
Content Studio agent generates from each section of a Growth DNA Profile.
Surfaced on the Creatives page under "Suggested Copies" and downloadable as
.txt / .docx.

Revision ID: a7f2c9d4e6b1
Revises: f4d6b8a0c2e5
Create Date: 2026-06-26 09:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7f2c9d4e6b1'
down_revision: Union[str, None] = 'f4d6b8a0c2e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suggested_copies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('growth_dna_profile_id', sa.UUID(), nullable=True),
        sa.Column('agent_run_id', sa.UUID(), nullable=True),
        sa.Column('product_name', sa.String(length=255), nullable=False),
        sa.Column(
            'copy_type',
            sa.Enum(
                'keywords', 'ad_copy', 'landing_page', 'email', 'social_post',
                'blog_outline', 'meta_tags',
                name='suggested_copy_type',
            ),
            nullable=False,
        ),
        sa.Column('section', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('model_used', sa.String(length=64), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'], ['workspaces.id'],
            name=op.f('fk_suggested_copies_workspace_id_workspaces'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['growth_dna_profile_id'], ['growth_dna_profiles.id'],
            name=op.f('fk_suggested_copies_growth_dna_profile_id_growth_dna_profiles'),
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['agent_run_id'], ['agent_runs.id'],
            name=op.f('fk_suggested_copies_agent_run_id_agent_runs'),
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_suggested_copies')),
    )
    op.create_index(
        op.f('ix_suggested_copies_workspace_id'),
        'suggested_copies', ['workspace_id'], unique=False,
    )
    op.create_index(
        op.f('ix_suggested_copies_growth_dna_profile_id'),
        'suggested_copies', ['growth_dna_profile_id'], unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_suggested_copies_growth_dna_profile_id'),
        table_name='suggested_copies',
    )
    op.drop_index(
        op.f('ix_suggested_copies_workspace_id'),
        table_name='suggested_copies',
    )
    op.drop_table('suggested_copies')
    op.execute('DROP TYPE IF EXISTS suggested_copy_type')
