"""Baseline schema, including idea stats and plan idea choices.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-27
"""

from __future__ import annotations

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

# Frozen copy of the schema this revision introduced. Later tables get their own revision.
_BASELINE = """
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY, owner TEXT, created_at TEXT NOT NULL, opened_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_versions (
  plan_id TEXT NOT NULL, version INTEGER NOT NULL, request_json TEXT NOT NULL,
  reason TEXT NOT NULL, created_at TEXT NOT NULL, ideas_json TEXT NOT NULL DEFAULT 'null',
  PRIMARY KEY (plan_id, version)
);
CREATE TABLE IF NOT EXISTS users (
  token_hash TEXT PRIMARY KEY, email_hash TEXT NOT NULL, adult_attested INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (
  owner TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, source TEXT NOT NULL,
  updated_at TEXT NOT NULL, PRIMARY KEY (owner, key)
);
CREATE TABLE IF NOT EXISTS spends (
  id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, amount TEXT NOT NULL, category TEXT NOT NULL,
  line_id TEXT, note TEXT, day INTEGER, idem_key TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE (plan_id, idem_key)
);
CREATE TABLE IF NOT EXISTS proposals (
  id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, base_version INTEGER NOT NULL,
  request_json TEXT NOT NULL, summary TEXT NOT NULL, delta TEXT NOT NULL,
  raises_total INTEGER NOT NULL, token_hash TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_spend (
  scope TEXT PRIMARY KEY, usd TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS magic_links (
  token_hash TEXT PRIMARY KEY, email TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
  id TEXT PRIMARY KEY, message TEXT NOT NULL, contact TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signin_attempts (
  email_hash TEXT NOT NULL, attempted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idea_stats (
  option_id TEXT PRIMARY KEY,
  shown INTEGER NOT NULL DEFAULT 0,
  kept INTEGER NOT NULL DEFAULT 0,
  swapped INTEGER NOT NULL DEFAULT 0
);
"""


def upgrade() -> None:
    for statement in _BASELINE.split(";"):
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
