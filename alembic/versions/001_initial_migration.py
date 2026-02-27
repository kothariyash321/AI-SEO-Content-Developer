"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2025-02-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create generation_jobs table
    op.create_table(
        'generation_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('topic', sa.String(length=500), nullable=False),
        sa.Column('target_word_count', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('config_json', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create pipeline_steps table
    op.create_table(
        'pipeline_steps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('step_name', sa.String(length=50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['generation_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create article_outputs table
    op.create_table(
        'article_outputs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('output_json', sa.JSON(), nullable=False),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['generation_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )


def downgrade() -> None:
    op.drop_table('article_outputs')
    op.drop_table('pipeline_steps')
    op.drop_table('generation_jobs')
