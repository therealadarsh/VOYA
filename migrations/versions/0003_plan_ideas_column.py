"""Add plan_versions.ideas_json to databases made before the idea bank.

0001_baseline uses CREATE TABLE IF NOT EXISTS, so it leaves an older
plan_versions table without this column. This revision adds it when missing.

Revision ID: 0003_plan_ideas_column
Revises: 0002_places
Create Date: 2026-11-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_plan_ideas_column"
down_revision = "0002_places"
branch_labels = None
depends_on = None


def _has_ideas_json() -> bool:
    columns = sa.inspect(op.get_bind()).get_columns("plan_versions")
    return any(column["name"] == "ideas_json" for column in columns)


def upgrade() -> None:
    if not _has_ideas_json():
        op.execute("ALTER TABLE plan_versions ADD COLUMN ideas_json TEXT NOT NULL DEFAULT 'null'")


def downgrade() -> None:
    # The baseline already defines ideas_json, so a downgrade keeps it.
    pass
