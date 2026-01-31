"""Add per-model + per-field filters and optional auth header to ir_webhooks.

Revision ID: f6a1b2c3d007
Revises: e5f1a2b3c006
Create Date: 2026-05-04

The base webhook subscriber row used to fan out every record event to
every webhook in the tenant; this migration adds four columns so an
operator can:

  * scope a webhook to a single model           (`model_filter`)
  * gate `record.updated` on specific fields    (`field_filter` JSON list)
  * inject a custom auth header on delivery     (`auth_header_name` /
                                                 `auth_header_value`)

The HMAC signature on `X-Orbiteus-Signature` is unaffected; auth_header_*
is *additional* (e.g. `Authorization: Bearer <token>` for receivers
that gate webhooks behind a header on top of HMAC verification).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a1b2c3d007"
down_revision: Union[str, None] = "e5f1a2b3c006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116838)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116838)")


def upgrade() -> None:
    _advisory_lock()
    try:
        op.add_column(
            "ir_webhooks",
            sa.Column("model_filter", sa.String(length=128), nullable=True),
        )
        op.add_column(
            "ir_webhooks",
            sa.Column("field_filter", sa.JSON(), server_default="[]", nullable=False),
        )
        op.add_column(
            "ir_webhooks",
            sa.Column("auth_header_name", sa.String(length=64), nullable=True),
        )
        op.add_column(
            "ir_webhooks",
            sa.Column("auth_header_value", sa.String(length=512), nullable=True),
        )
        op.create_index(
            op.f("ix_ir_webhooks_model_filter"),
            "ir_webhooks",
            ["model_filter"],
        )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.drop_index(op.f("ix_ir_webhooks_model_filter"), table_name="ir_webhooks")
        op.drop_column("ir_webhooks", "auth_header_value")
        op.drop_column("ir_webhooks", "auth_header_name")
        op.drop_column("ir_webhooks", "field_filter")
        op.drop_column("ir_webhooks", "model_filter")
    finally:
        _advisory_unlock()
