"""unique publication_id (Revises 87e9b1ca66b8)"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '401dce8c4864'
down_revision: Union[str, Sequence[str], None] = '87e9b1ca66b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_dashboard_publications_publication_id", "dashboard_publications", ["publication_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_dashboard_publications_publication_id", "dashboard_publications", type_="unique")
