"""Add recovery_codes_hashed to base_users.

Revision ID: e5f1a2b3c006
Revises: d4c0a1f2e005
Create Date: 2026-05-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f1a2b3c006"
down_revision: Union[str, None] = "d4c0a1f2e005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116837)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116837)")


def upgrade() -> None:
    _advisory_lock()
    try:
        op.add_column(
            "base_users",
            sa.Column("recovery_codes_hashed", sa.JSON(), server_default="[]", nullable=False),
        )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.drop_column("base_users", "recovery_codes_hashed")
    finally:
        _advisory_unlock()
