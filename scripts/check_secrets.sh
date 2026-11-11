#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if git -C "$ROOT" grep -nE 'sk-[A-Za-z0-9]{20,}|OPENROUTER_API_KEY=[^$\s]' -- ':!*.example' ':!.env.example' 2>/dev/null; then
  echo "check_secrets: possible secret in tree"
  exit 1
fi
echo "check_secrets: ok"
