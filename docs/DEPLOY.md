# Deploy VOYA on AWS (MVP)

Target: one small container (API + built React static files) and Lightsail Postgres or RDS,
US region, HTTPS, secrets in AWS Secrets Manager, **Budgets alarm at $20/month**.

## Prerequisites

- AWS account with ~$100 credits
- Domain (optional) pointing at load balancer
- `OPENROUTER_API_KEY`, `FOURSQUARE_API_KEY` (optional) in secrets

## Build

```sh
uv sync
cd web && npm ci && npm run build
docker build -t voya .
```

## Runtime env

| Name | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://...` (SQLite omitted in prod) |
| `VOYA_DEV_SIGNIN` | `0` (magic link; use SES or similar) |
| `VOYA_PUBLIC_URL` | `https://your.domain` |
| `VOYA_CITED_RULES` | `1` |

## Budget alarm

Create an AWS Budgets monthly cost budget with email alert at **$20**.

## Smoke test

1. Open `/` on a phone width (~360px).
2. Plan Chicago → see est. total + demo banner.
3. Sign in (magic link) → save trip → log spend.

This guide is intentionally short; refine with your chosen Lightsail/ECS template when provisioning.
