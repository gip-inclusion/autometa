"""Index trigramme de la recherche étendu au fil Slack des conversations venues de Slack."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "8d1f4c6a2e37"
down_revision: Union[str, Sequence[str], None] = "5b7d2e9c41a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def rebuild(types: str) -> None:
    # Why: hors transaction et CONCURRENTLY — une création ordinaire bloquerait l'écriture des messages, donc tous
    # les tours en cours, le temps de construire l'index. Une construction interrompue laisse un index invalide
    # sous ce nom : on le retire avant de recommencer.
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_messages_search")
        op.create_index(
            "idx_messages_search",
            "messages",
            ["content"],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={"content": "gin_trgm_ops"},
            postgresql_where=sa.text(f"type IN ({types})"),
            postgresql_concurrently=True,
        )


def upgrade() -> None:
    rebuild("'user', 'assistant', 'slack_context'")


def downgrade() -> None:
    rebuild("'user', 'assistant'")
