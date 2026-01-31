"""CRM rename: Person/Lead/Stage/Team (ADR-0008, PR 9).

- Drops legacy `crm_customers`, `crm_opportunities`, `crm_pipelines`.
- Recreates `crm_stages` (legacy had `pipeline_id`/`fold`; canonical has
  neither and uses `fold_in_kanban`).
- Creates `crm_persons`, `crm_teams`, `crm_leads`.

Revision ID: d4c0a1f2e005
Revises: c3b5d2e1c004
Create Date: 2026-05-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4c0a1f2e005"
down_revision: Union[str, None] = "c3b5d2e1c004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116837)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116837)")


# Columns added by PR 3 to BaseModel — repeated here so we don't omit them.
def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("custom_fields", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("modified_by_id", sa.UUID(), nullable=True),
    ]


def upgrade() -> None:
    _advisory_lock()
    try:
        # 1) Drop legacy CRM tables. Use IF EXISTS for safety against partial states.
        op.execute("DROP TABLE IF EXISTS crm_opportunities CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_customers CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_pipelines CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_stages CASCADE")

        # 2) Recreate crm_stages in canonical shape.
        op.create_table(
            "crm_stages",
            *_base_columns(),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("sequence", sa.Integer(), server_default="10", nullable=False),
            sa.Column("probability", sa.Float(), server_default="0", nullable=False),
            sa.Column("is_won", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("is_lost", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("fold_in_kanban", sa.Boolean(), server_default="false", nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_stages")),
        )
        op.create_index(op.f("ix_crm_stages_tenant_id"), "crm_stages", ["tenant_id"])
        op.create_index(op.f("ix_crm_stages_company_id"), "crm_stages", ["company_id"])

        # 3) crm_persons
        op.create_table(
            "crm_persons",
            *_base_columns(),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("mobile", sa.String(length=50), nullable=True),
            sa.Column("kind", sa.String(length=20), server_default="contact", nullable=False),
            sa.Column("is_company", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("vat", sa.String(length=50), nullable=True),
            sa.Column("website", sa.String(length=255), nullable=True),
            sa.Column("street", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=100), nullable=True),
            sa.Column("country_code", sa.String(length=5), server_default="PL", nullable=False),
            sa.Column("assigned_user_id", sa.UUID(), nullable=True),
            sa.Column("assigned_team_id", sa.UUID(), nullable=True),
            sa.Column("tags", sa.JSON(), server_default="[]", nullable=False),
            sa.Column("source", sa.String(length=50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_persons")),
        )
        op.create_index(op.f("ix_crm_persons_tenant_id"), "crm_persons", ["tenant_id"])
        op.create_index(op.f("ix_crm_persons_company_id"), "crm_persons", ["company_id"])
        op.create_index(op.f("ix_crm_persons_kind"), "crm_persons", ["kind"])

        # 4) crm_teams
        op.create_table(
            "crm_teams",
            *_base_columns(),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("leader_user_id", sa.UUID(), nullable=True),
            sa.Column("member_user_ids", sa.JSON(), server_default="[]", nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_teams")),
        )
        op.create_index(op.f("ix_crm_teams_tenant_id"), "crm_teams", ["tenant_id"])
        op.create_index(op.f("ix_crm_teams_company_id"), "crm_teams", ["company_id"])

        # 5) crm_leads
        op.create_table(
            "crm_leads",
            *_base_columns(),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("person_id", sa.UUID(), nullable=True),
            sa.Column("stage_id", sa.UUID(), nullable=True),
            sa.Column("assigned_user_id", sa.UUID(), nullable=True),
            sa.Column("assigned_team_id", sa.UUID(), nullable=True),
            sa.Column("expected_revenue", sa.Float(), server_default="0", nullable=False),
            sa.Column("probability", sa.Float(), server_default="0", nullable=False),
            sa.Column("expected_close_date", sa.Date(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("lost_reason", sa.String(length=500), nullable=True),
            sa.Column("tags", sa.JSON(), server_default="[]", nullable=False),
            sa.ForeignKeyConstraint(["person_id"], ["crm_persons.id"]),
            sa.ForeignKeyConstraint(["stage_id"], ["crm_stages.id"]),
            sa.ForeignKeyConstraint(["assigned_team_id"], ["crm_teams.id"]),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_leads")),
        )
        op.create_index(op.f("ix_crm_leads_tenant_id"), "crm_leads", ["tenant_id"])
        op.create_index(op.f("ix_crm_leads_company_id"), "crm_leads", ["company_id"])
        op.create_index(op.f("ix_crm_leads_stage_id"), "crm_leads", ["stage_id"])
        op.create_index(op.f("ix_crm_leads_person_id"), "crm_leads", ["person_id"])
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.execute("DROP TABLE IF EXISTS crm_leads CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_teams CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_persons CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_stages CASCADE")
        # Legacy schema is not restored; if you need it, downgrade past
        # the initial migration (b04954bd8aec) and replay from scratch.
    finally:
        _advisory_unlock()
