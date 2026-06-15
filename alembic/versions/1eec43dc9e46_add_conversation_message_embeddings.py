"""add conversation message embeddings

Revision ID: 1eec43dc9e46
Revises: df20b48b49c5
Create Date: 2026-06-15 16:23:29.199928

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1eec43dc9e46"
down_revision: Union[str, Sequence[str], None] = "7397f669848c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE conversation_message_embeddings (
            id BIGSERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            user_id TEXT,
            role TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            content_length INTEGER NOT NULL,
            content_preview TEXT,
            message_timestamp TIMESTAMPTZ NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding vector(384) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_conversation_message_embeddings_message_model
                UNIQUE (message_id, embedding_model)
        )
        """)

    op.execute("""
        CREATE INDEX idx_conversation_message_embeddings_conversation_id
        ON conversation_message_embeddings (conversation_id)
        """)

    op.execute("""
        CREATE INDEX idx_conversation_message_embeddings_user_id
        ON conversation_message_embeddings (user_id)
        """)

    op.execute("""
        CREATE INDEX idx_conversation_message_embeddings_model
        ON conversation_message_embeddings (embedding_model)
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_conversation_message_embeddings_model")
    op.execute("DROP INDEX IF EXISTS idx_conversation_message_embeddings_user_id")
    op.execute(
        "DROP INDEX IF EXISTS idx_conversation_message_embeddings_conversation_id"
    )
    op.execute("DROP TABLE IF EXISTS conversation_message_embeddings")
