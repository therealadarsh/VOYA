# Deploy VOYA

Two ways to run the production container. Neither path is provisioned from
this repo: deploying needs the owner's hosting account (see **Blocked**).

The image is `Dockerfile`. It listens on port 8000, runs as uid 10001, stores
SQLite at `VOYA_DATA_DIR` (default `/data`), and **exits on startup** when
`VOYA_ENV=production` and any required setting is missing. The questions it
prints are the ones to answer before a real start.

Required when `VOYA_ENV=production`:

| Name | Purpose |
|---|---|
| `VOYA_INVITE_CODE` | Private-preview code, 8 or more characters |
| `VOYA_PUBLIC_URL` | `https://` origin used in magic links |
| `VOYA_DEV_SIGNIN` | `0` so sign-in sends email |
| `VOYA_DATA_DIR` | Absolute directory that survives redeploys |
| `VOYA_SMTP_HOST` | SMTP server |
| `VOYA_SMTP_PORT` | Usually `587` |
| `VOYA_SMTP_USERNAME` | SMTP user |
| `VOYA_SMTP_PASSWORD` | SMTP password |
| `VOYA_SMTP_FROM` | From address on magic-link mail |

Put secrets in the host's secret store or a gitignored `.env`. Do not bake
them into the image.

## 1. Simple host (Docker Compose)

A single Linux machine with Docker. HTTPS terminates at a reverse proxy on
the same machine (Caddy or nginx). The app container speaks HTTP on loopback.

```sh
docker compose build
docker compose run --rm --entrypoint .venv/bin/alembic voya upgrade head
docker compose up -d
```

`docker-compose.yml` mounts a named volume on `/data`. The database file is
`/data/voya.db`. Redeploying keeps that volume: run `docker compose build`,
the same migrate line, then `docker compose up -d`. Production refuses to
start on a database that is not at the latest migration (see Migrations).

Backups use SQLite's backup API and write into the same volume:

```sh
docker compose exec voya .venv/bin/python -m voya.backup
```

Run that from cron. Copy `voya-*.db` off the machine as well; a volume that
dies with the disk is not a backup. Restore by stopping the app and replacing
`/data/voya.db` with a chosen backup file.

Point the proxy at `127.0.0.1:8000`. The proxy owns the certificate. The
container sends `Strict-Transport-Security` only when `VOYA_ENV=production`.

## Client address

Rate limits and the anonymous AI-spend scope use one helper,
`client_address`. It trusts `X-Forwarded-For` only when the direct peer is
listed in `VOYA_TRUSTED_PROXY_IPS`. The value used is the right-most hop that
is not itself in that list. An empty setting (the default) ignores the
header, so a caller cannot pick their own address.

The image starts uvicorn with `--no-proxy-headers` and an empty
`--forwarded-allow-ips`. Uvicorn therefore leaves `request.client.host` as
the peer that opened the socket. Do not turn proxy headers on in the command
or every bucket collapses to one address again.

| Host | What to set |
|---|---|
| No proxy (the process is reached directly) | Leave `VOYA_TRUSTED_PROXY_IPS` empty. |
| Docker Compose reverse proxy on the same machine | The address the app container sees for the proxy (often the compose-network gateway). Read it from the proxy container or from a connection to the app; do not guess a public address. |
| Render | The proxy addresses Render uses to connect to the service. Leave the setting empty until those addresses are known. |
| Fly | The edge addresses Fly uses as the peer. Leave the setting empty until those addresses are known. |
| AWS load balancer (App Runner, Lightsail, or ECS) | The load balancer's private addresses, the only peers the task should accept. Leave the setting empty until those addresses are known. |

Smoke check:

```sh
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz
```

`/healthz` is liveness (the process is up). `/readyz` is readiness (the
database answers `SELECT 1`). Logs are JSON on stdout (`VOYA_LOG_FORMAT=json`).
Access lines include the path and status, not the query string, so magic-link
tokens are not logged.

`/metrics` is Prometheus text: request count, error count, and total duration.
In production the process refuses to start if `VOYA_METRICS_TOKEN` is missing.
Send that token as `X-Metrics-Token`. A wrong token is 401. In development,
with no token set, `/metrics` stays open. Point the host's scraper (or
CloudWatch agent plus a sidecar) at that URL. No monitoring vendor account is
created from this repo.

## Migrations

`make migrate` runs `alembic upgrade head` on the database chosen by `VOYA_DB`,
then `DATABASE_URL`, then `VOYA_DATA_DIR/voya.db`. The same revisions apply to
SQLite and Postgres. Production refuses to start when that database is not at
the latest revision. Run `make migrate` before the new process starts,
including the first boot.

With Docker Compose the SQLite file lives in the `voya-data` volume, so
`make migrate` on the host would migrate a different file. Run the migration
inside the image instead, before `docker compose up`:

```sh
docker compose run --rm --entrypoint .venv/bin/alembic voya upgrade head
```

If you skip it, the container refuses to start and Compose keeps restarting it.

To copy an existing SQLite file into a database that has already been migrated:

```sh
python -m voya.copy_db --from var/voya.db --to "$DATABASE_URL" --dry-run
python -m voya.copy_db --from var/voya.db --to "$DATABASE_URL"
```

The command prints a row count per table and does not print the URL. It stops
if the target already has rows, unless you pass `--force`.

## Smoke test

`scripts/smoke.sh` builds the image, migrates a temporary volume, and checks
`/healthz`, `/readyz`, `/privacy`, a plan request without the invite cookie,
a New York plan after unlock, `/metrics` without a token, and that the process
is not root. It removes the container and the volume when it finishes. If
Docker is not running it prints `Docker is not running.` and exits non-zero.
The `docker` CI job runs this script.

## After deploy

1. `make migrate` finished against the production database.
2. `/healthz` and `/readyz` return 200.
3. `/privacy` returns 200.
4. `POST /v1/plans` without the invite cookie returns 401.
5. `/metrics` without `X-Metrics-Token` returns 401, and with the token returns 200.
6. The process user is not root (`id -u` is not 0).
7. `VOYA_TRUSTED_PROXY_IPS` is still empty unless the proxy's peer addresses are known.
8. The Demo prices banner is still visible. Place prices are still the synthetic catalog.

## 2. AWS

Use the same image. This is a guide, not a provisioned account.

1. Build the image and push it to a private ECR repository in the region you
   choose.
2. Run it as one small service (App Runner, Lightsail containers, or ECS
   Fargate) with the environment variables above in Secrets Manager, not in
   the task definition in plain text.
3. Put a load balancer or App Runner HTTPS endpoint in front. Set
   `VOYA_PUBLIC_URL` to that `https://` origin.
4. For the private preview, SQLite on a volume is enough. For the public MVP,
   set `DATABASE_URL` to a Postgres URL (`postgresql://...`). The app uses
   that URL instead of the SQLite file. Back up with `pg_dump` from the host.
   Do not put the URL on a command line if it contains a password. RDS or
   Lightsail Postgres both fit. This guide does not create the database.
5. Schedule `python -m voya.backup` and copy the file to a private S3 bucket
   you control. Keep the bucket from public ACLs.
6. Ship container stdout to CloudWatch Logs. The JSON lines are the app log.
7. Alarms: `/readyz` failing, and a monthly cost alarm. `docs/BUILD_PLAN.md`
   recorded **$20** as a working figure. Confirm or replace that amount
   before creating the alarm (see **Blocked**). This guide does not create
   the alarm.

Security group: the task accepts traffic from the load balancer only. The
database port is not public because the preview uses a file on the volume.

## Blocked

These need the owner. The container and this guide do not guess them.

- Which hosting account should the private preview be deployed to?
- What SMTP host, port, username, password, and From address should
  magic-link email use?
- What invite code should the private preview require?
- What public https URL should magic links use?
- What monthly hosting budget should the AWS cost alarm use? BUILD_PLAN
  recorded $20; confirm or replace it before any alarm is created.
- What wording should the Privacy page and the Terms page use? The pages
  shipped here are drafts and say so. They are not legal text.
- What is the Foursquare API key, the monthly budget in USD, and the USD to
  count per search? Live place search stays off until `FOURSQUARE_API_KEY`,
  `VOYA_PLACES_BUDGET_USD`, `VOYA_PLACES_USD_PER_CALL`, and
  `VOYA_PLACES_LIVE=1` are set. The demo banner stays up while place prices
  are still the synthetic catalog.

## Local image check

Override the production defaults when you only want to see the process boot:

```sh
docker run --rm -p 8000:8000 \
  -e VOYA_ENV=development \
  -e VOYA_DEV_SIGNIN=1 \
  -e VOYA_DATA_DIR=/data \
  voya
```

Development sign-in returns a token in the response. Production does not.
