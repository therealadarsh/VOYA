"""Canonical places cache.

Revision ID: 0002_places
Revises: 0001_baseline
Create Date: 2026-11-27
"""

from __future__ import annotations

from alembic import op

revision = "0002_places"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

_PLACES = """
CREATE TABLE IF NOT EXISTS places (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  tags TEXT NOT NULL,
  lat TEXT NOT NULL,
  lng TEXT NOT NULL,
  hours TEXT,
  provider_ids TEXT NOT NULL,
  source TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  cache_until TEXT NOT NULL
)
"""


def upgrade() -> None:
    op.execute(_PLACES)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS places")
