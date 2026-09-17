"""État par moteur (session native, dernier message vu) porté par conversations.engine_state."""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "dc37fe3e0e50"
down_revision: Union[str, Sequence[str], None] = "d3f5a8c1b607"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("engine_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "engine_state")
