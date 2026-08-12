"""Termes proposés depuis l'app : utilisables mais hors vocabulaire du tagueur."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d3f5a8c1b607"
down_revision: Union[str, Sequence[str], None] = "c7d2b90e4f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tags", sa.Column("pending", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("idx_tags_pending", "tags", ["pending"], postgresql_where=sa.text("pending"))


def downgrade() -> None:
    op.drop_index("idx_tags_pending", table_name="tags")
    op.drop_column("tags", "pending")
