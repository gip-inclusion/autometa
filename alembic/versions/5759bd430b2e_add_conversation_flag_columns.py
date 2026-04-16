"""add conversation flag columns"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5759bd430b2e'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column('flagged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversations', sa.Column('flag_reason', sa.Text(), nullable=True))
    op.add_column('conversations', sa.Column('flag_user_id', sa.Text(), nullable=True))
    op.create_index(
        'idx_conversations_flagged',
        'conversations',
        ['flagged_at'],
        unique=False,
        postgresql_where=sa.text('flagged_at IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'idx_conversations_flagged',
        table_name='conversations',
        postgresql_where=sa.text('flagged_at IS NOT NULL'),
    )
    op.drop_column('conversations', 'flag_user_id')
    op.drop_column('conversations', 'flag_reason')
    op.drop_column('conversations', 'flagged_at')
