"""Outbox + webhooks

Adds:
- ir_outbox table (durable side-effect queue, ADR-0010, docs/12-events-and-queues.md)
- ir_webhooks table (outbound webhook subscribers)

Revision ID: b2a4e1c0d003
Revises: a1f3c0e1b002
Create Date: 2026-05-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2a4e1c0d003"
down_revision: Union[str, None] = "a1f3c0e1b002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116837)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116837)")


def upgrade() -> None:
    _advisory_lock()
    try:
        # ir_outbox
        op.create_table(
            "ir_outbox",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
            sa.Column("event", sa.String(length=255), nullable=False),
            sa.Column("payload", sa.JSON(), server_default="{}", nullable=False),
            sa.Column("target_kind", sa.String(length=50), nullable=True),
            sa.Column("target_ref", sa.String(length=255), nullable=True),
            sa.Column("retries", sa.Integer(), server_default="0", nullable=False),
            sa.Column("next_run_at", sa.String(length=50), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_ir_outbox")),
        )
        op.create_index(op.f("ix_ir_outbox_tenant_id"), "ir_outbox", ["tenant_id"])
        op.create_index(op.f("ix_ir_outbox_status"), "ir_outbox", ["status"])
        op.create_index(op.f("ix_ir_outbox_event"), "ir_outbox", ["event"])
        op.create_index(op.f("ix_ir_outbox_target_kind"), "ir_outbox", ["target_kind"])
        op.create_index(op.f("ix_ir_outbox_next_run_at"), "ir_outbox", ["next_run_at"])
        # Hot path: drainer scans pending rows due for execution.
        op.create_index(
            "ix_ir_outbox_status_next_run_at",
            "ir_outbox",
            ["status", "next_run_at"],
        )

        # ir_webhooks (BaseModel — has tenant_id, attribution columns).
        op.create_table(
            "ir_webhooks",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("company_id", sa.UUID(), nullable=True),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("custom_fields", sa.JSON(), server_default="{}", nullable=False),
            sa.Column("created_by_id", sa.UUID(), nullable=True),
            sa.Column("modified_by_id", sa.UUID(), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("url", sa.String(length=2048), nullable=False),
            sa.Column("secret", sa.String(length=255), nullable=False),
            sa.Column("event_mask", sa.JSON(), server_default="[]", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("last_delivery_at", sa.String(length=50), nullable=True),
            sa.Column("last_delivery_status", sa.String(length=50), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_ir_webhooks")),
        )
        op.create_index(op.f("ix_ir_webhooks_tenant_id"), "ir_webhooks", ["tenant_id"])
        op.create_index(op.f("ix_ir_webhooks_company_id"), "ir_webhooks", ["company_id"])
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.drop_index(op.f("ix_ir_webhooks_company_id"), table_name="ir_webhooks")
        op.drop_index(op.f("ix_ir_webhooks_tenant_id"), table_name="ir_webhooks")
        op.drop_table("ir_webhooks")

        op.drop_index("ix_ir_outbox_status_next_run_at", table_name="ir_outbox")
        op.drop_index(op.f("ix_ir_outbox_next_run_at"), table_name="ir_outbox")
        op.drop_index(op.f("ix_ir_outbox_target_kind"), table_name="ir_outbox")
        op.drop_index(op.f("ix_ir_outbox_event"), table_name="ir_outbox")
        op.drop_index(op.f("ix_ir_outbox_status"), table_name="ir_outbox")
        op.drop_index(op.f("ix_ir_outbox_tenant_id"), table_name="ir_outbox")
        op.drop_table("ir_outbox")
    finally:
        _advisory_unlock()
