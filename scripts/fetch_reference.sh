#!/usr/bin/env bash
# Fetch the read-only Daytrip reference (MIT, see its package.json) at a pinned
# commit into reference/daytrip/. The folder is gitignored: we read it, we do
# not vendor it. Safe to run twice.
set -euo pipefail

REPO_URL="https://github.com/ArabotHXL/trip-planner"
PINNED_SHA="74610afbccd23264997c28d5d77a8f8c3a7a248f"
DEST="$(cd "$(dirname "$0")/.." && pwd)/reference/daytrip"

if [ -d "$DEST/.git" ]; then
  have="$(git -C "$DEST" rev-parse HEAD 2>/dev/null || echo none)"
  if [ "$have" = "$PINNED_SHA" ]; then
    echo "reference/daytrip already at $PINNED_SHA"
  else
    echo "reference/daytrip exists at $have, expected $PINNED_SHA." >&2
    echo "Delete it and re-run to refetch." >&2
    exit 1
  fi
  exit 0
fi

git init -q "$DEST"
git -C "$DEST" remote add origin "$REPO_URL"
git -C "$DEST" fetch -q --depth 1 origin "$PINNED_SHA"
git -C "$DEST" checkout -q FETCH_HEAD
echo "Fetched Daytrip $PINNED_SHA into reference/daytrip"
