"""Désactive le vocabulaire hérité : seuls les tags venus de Notion restent actifs."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c7d2b90e4f31"
down_revision: Union[str, Sequence[str], None] = "a1c4e77b21d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Why: les assignations sont conservées — on retire seulement les termes du vocabulaire
    # offert ; la purge définitive se fait après relecture (lib.tag_sync.purge_legacy_tags).
    op.execute(sa.text("UPDATE tags SET active = false WHERE notion_page_id IS NULL"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE tags SET active = true WHERE notion_page_id IS NULL"))
