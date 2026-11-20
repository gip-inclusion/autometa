"""Index trigramme sur les échanges, pour la recherche de conversations par mots."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "3a555009668b"
down_revision: Union[str, Sequence[str], None] = "3c5d8e1f9a72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Why: hors transaction et CONCURRENTLY — une création ordinaire bloquerait l'écriture des
    # messages, donc tous les tours en cours, le temps de construire l'index.
    with op.get_context().autocommit_block():
        op.create_index(
            "idx_messages_search",
            "messages",
            ["content"],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={"content": "gin_trgm_ops"},
            postgresql_where=sa.text("type IN ('user', 'assistant')"),
            postgresql_concurrently=True,
            if_not_exists=True,
        )


def downgrade() -> None:
    op.drop_index("idx_messages_search", table_name="messages")
