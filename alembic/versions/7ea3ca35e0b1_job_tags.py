"""Tags des pipelines de jobs : une ligne par couple (pipeline, tag), sur le vocabulaire commun."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "7ea3ca35e0b1"
down_revision: Union[str, Sequence[str], None] = "046795c5db73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_tags",
        sa.Column("pipeline_id", sa.Text(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pipeline_id", "tag_id"),
    )
    op.create_index("idx_job_tags_tag", "job_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_job_tags_tag", table_name="job_tags")
    op.drop_table("job_tags")
