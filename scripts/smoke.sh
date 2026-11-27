#!/usr/bin/env bash
# Build the production image and check the preview gates with test-only values.
set -euo pipefail

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker, then run scripts/smoke.sh again." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="voya-smoke-$$"
IMAGE="voya-smoke:local"
PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
VOL="voya-smoke-data-$$"

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker volume create "$VOL" >/dev/null
docker build -t "$IMAGE" "$ROOT"

docker run --rm \
  -v "${VOL}:/data" \
  -e VOYA_DATA_DIR=/data \
  -e VOYA_DB= \
  -e DATABASE_URL= \
  --entrypoint .venv/bin/alembic \
  "$IMAGE" upgrade head

docker run -d --name "$NAME" \
  -p "127.0.0.1:${PORT}:8000" \
  -v "${VOL}:/data" \
  -e VOYA_ENV=production \
  -e VOYA_DEV_SIGNIN=0 \
  -e VOYA_INVITE_CODE=smoke-invite \
  -e VOYA_PUBLIC_URL=https://preview.example \
  -e VOYA_DATA_DIR=/data \
  -e VOYA_SMTP_HOST=smtp.example \
  -e VOYA_SMTP_PORT=587 \
  -e VOYA_SMTP_USERNAME=voya \
  -e VOYA_SMTP_PASSWORD=smoke-secret \
  -e VOYA_SMTP_FROM=sign-in@example.com \
  -e VOYA_METRICS_TOKEN=smoke-metrics-token \
  "$IMAGE" >/dev/null

ready=0
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done
if [[ "$ready" -ne 1 ]]; then
  echo "The container did not become ready." >&2
  docker logs "$NAME" >&2 || true
  exit 1
fi

check() {
  local path="$1"
  local want="$2"
  shift 2
  local got
  got="$(curl -s -o /dev/null -w "%{http_code}" "$@" "http://127.0.0.1:${PORT}${path}")"
  if [[ "$got" != "$want" ]]; then
    echo "${path} returned ${got}, expected ${want}" >&2
    exit 1
  fi
}

PLAN='{"destination":"new-york","start_date":"2026-12-05","days":1,"budget":"400","firmness":"wiggle","party":{"adults":1}}'

check /healthz 200
check /readyz 200
check /privacy 200
check /v1/plans 401 -X POST -H "Content-Type: application/json" -d "$PLAN"
check /metrics 401

# Production cookies are Secure. This run talks to localhost over HTTP, so curl
# will not resend that cookie. Send the value the unlock response set.
headers="$(mktemp)"
unlock_code="$(curl -s -D "$headers" -o /dev/null -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d '{"code":"smoke-invite"}' \
  "http://127.0.0.1:${PORT}/v1/preview/unlock")"
cookie="$(grep -i '^set-cookie: voya_preview=' "$headers" | head -n 1 | tr -d '\r' | cut -d';' -f1 | cut -d'=' -f2 || true)"
rm -f "$headers"
if [[ "$unlock_code" != "200" || -z "${cookie}" ]]; then
  echo "Unlock did not set the preview cookie (HTTP ${unlock_code})." >&2
  exit 1
fi

plan_body="$(mktemp)"
plan_code="$(curl -s -o "$plan_body" -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -H "Cookie: voya_preview=${cookie}" \
  -d "$PLAN" \
  "http://127.0.0.1:${PORT}/v1/plans")"
if [[ "$plan_code" != "200" ]]; then
  echo "Planning NYC after unlock returned ${plan_code}, expected 200" >&2
  head -c 400 "$plan_body" >&2 || true
  echo >&2
  rm -f "$plan_body"
  exit 1
fi
rm -f "$plan_body"

uid="$(docker exec "$NAME" id -u)"
if [[ "$uid" == "0" ]]; then
  echo "The container is running as root." >&2
  exit 1
fi

echo "Smoke checks passed (uid ${uid})."
