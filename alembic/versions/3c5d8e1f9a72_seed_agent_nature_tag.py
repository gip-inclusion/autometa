"""Terme « agent » de la facette Nature, proposé d'emblée pour taguer les jobs."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "3c5d8e1f9a72"
down_revision: Union[str, Sequence[str], None] = "7ea3ca35e0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Why: « agent » doit exister sans attendre la synchro Notion ; proposé, il reste hors prompt du tagueur.
    op.execute(
        sa.text(
            "INSERT INTO tags (name, type, label, active, pending) "
            "VALUES ('agent', 'nature', 'Agent', true, true) ON CONFLICT (name) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM tags WHERE name = 'agent' AND pending AND notion_page_id IS NULL"))
