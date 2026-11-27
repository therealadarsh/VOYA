"""Baseline schema, including idea stats and plan idea choices.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-27
"""

from __future__ import annotations

from alembic import op

from voya.store import SCHEMA

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in SCHEMA.split(";"):
        sql = statement.strip()
        if sql:
            op.execute(sql)


def downgrade() -> None:
    for table in (
        "idea_stats",
        "signin_attempts",
        "feedback",
        "magic_links",
        "ai_spend",
        "proposals",
        "spends",
        "preferences",
        "users",
        "plan_versions",
        "plans",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
