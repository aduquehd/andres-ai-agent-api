"""Add favorite_foods and professional_experience to KB enum

Revision ID: f2a8c4b1e5d6
Revises: 9ad03f771076
Create Date: 2026-05-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f2a8c4b1e5d6"
down_revision: Union[str, None] = "9ad03f771076"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE knowledgebasetypeenum ADD VALUE IF NOT EXISTS 'favorite_foods'"
        )
        op.execute(
            "ALTER TYPE knowledgebasetypeenum ADD VALUE IF NOT EXISTS 'professional_experience'"
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not support removing values from an enum type. To revert,
    # the enum would need to be recreated and the column re-typed. Left as a
    # no-op intentionally.
    pass
