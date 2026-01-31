"""Audit log + attribution columns

Adds:
- ir_audit_log table (mandatory CRUD audit, ADR-0010, docs/14-audit.md)
- created_by_id / modified_by_id on every business table (BaseModel)

Revision ID: a1f3c0e1b002
Revises: b04954bd8aec
Create Date: 2026-05-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1f3c0e1b002"
down_revision: Union[str, None] = "b04954bd8aec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that use `make_base_columns` (BaseModel) — get audit attribution columns.
BUSINESS_TABLES: tuple[str, ...] = (
    "base_companies",
    "base_partners",
    "base_users",
    "ir_attachments",
    "crm_pipelines",
    "crm_stages",
    "crm_customers",
    "crm_opportunities",
)


def _advisory_lock() -> None:
    """pg_advisory_lock guard so concurrent migrate runs serialize.

    Stable lock id matches `orbiteus_core.alembic_lock.ORBITEUS_MIGRATION_LOCK_ID`.
    """
    bind = op.get_bind()
    bind.exec_driver_sql("SELECT pg_advisory_lock(11534116837)")


def _advisory_unlock() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("SELECT pg_advisory_unlock(11534116837)")


def upgrade() -> None:
    _advisory_lock()
    try:
        # 1) Audit log table.
        op.create_table(
            "ir_audit_log",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("actor", sa.String(length=20), server_default="system", nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("model", sa.String(length=255), nullable=False),
            sa.Column("record_id", sa.UUID(), nullable=True),
            sa.Column("operation", sa.String(length=50), nullable=False),
            sa.Column("diff", sa.JSON(), server_default="{}", nullable=False),
            sa.Column("metadata", sa.JSON(), server_default="{}", nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_ir_audit_log")),
        )
        op.create_index(op.f("ix_ir_audit_log_tenant_id"), "ir_audit_log", ["tenant_id"])
        op.create_index(op.f("ix_ir_audit_log_user_id"), "ir_audit_log", ["user_id"])
        op.create_index(op.f("ix_ir_audit_log_request_id"), "ir_audit_log", ["request_id"])
        op.create_index(op.f("ix_ir_audit_log_model"), "ir_audit_log", ["model"])
        op.create_index(op.f("ix_ir_audit_log_record_id"), "ir_audit_log", ["record_id"])
        op.create_index(op.f("ix_ir_audit_log_operation"), "ir_audit_log", ["operation"])
        # Hot path: list latest entries for a record.
        op.create_index(
            "ix_ir_audit_log_model_record_create",
            "ir_audit_log",
            ["model", "record_id", "create_date"],
        )

        # 2) Attribution columns on every business table.
        for tbl in BUSINESS_TABLES:
            op.add_column(
                tbl,
                sa.Column("created_by_id", sa.UUID(), nullable=True),
            )
            op.add_column(
                tbl,
                sa.Column("modified_by_id", sa.UUID(), nullable=True),
            )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        for tbl in BUSINESS_TABLES:
            op.drop_column(tbl, "modified_by_id")
            op.drop_column(tbl, "created_by_id")

        op.drop_index("ix_ir_audit_log_model_record_create", table_name="ir_audit_log")
        op.drop_index(op.f("ix_ir_audit_log_operation"), table_name="ir_audit_log")
        op.drop_index(op.f("ix_ir_audit_log_record_id"), table_name="ir_audit_log")
        op.drop_index(op.f("ix_ir_audit_log_model"), table_name="ir_audit_log")
        op.drop_index(op.f("ix_ir_audit_log_request_id"), table_name="ir_audit_log")
        op.drop_index(op.f("ix_ir_audit_log_user_id"), table_name="ir_audit_log")
        op.drop_index(op.f("ix_ir_audit_log_tenant_id"), table_name="ir_audit_log")
        op.drop_table("ir_audit_log")
    finally:
        _advisory_unlock()
