"""Initial empty migration

Revision ID: 27f6f65437cd
Revises: e28601d87962
Create Date: 2025-06-25 10:43:40.740184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27f6f65437cd'
down_revision: Union[str, Sequence[str], None] = 'e28601d87962'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
