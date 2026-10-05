"""cron task states — état d'activation des tâches système, hors image."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5be6c06429dd"
down_revision: Union[str, Sequence[str], None] = "dc37fe3e0e50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cron_task_states",
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("cron_task_states")
