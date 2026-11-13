run:
	uv run uvicorn voya.api:app --reload --port 8000

test:
	uv run pytest -q -p no:warnings

verify: sync lint typecheck test policy citations traceability secrets examples

sync:
	uv sync --frozen

lint:
	uv run ruff check src/voya/cost src/voya/pricing src/voya/data src/voya/accounts src/voya/settings.py src/voya/log.py src/voya/backup.py src/voya/preview.py src/voya/safety.py src/voya/db.py src/voya/metrics.py src/voya/ideas.py src/voya/providers scripts tests/test_m1_data.py tests/test_m2_cited_planner.py tests/test_m4_magic_link.py tests/test_p1_preview.py tests/test_p1_nyc.py tests/test_p1_a11y.py
	uv run ruff format --check src/voya/cost src/voya/pricing src/voya/data src/voya/accounts src/voya/settings.py src/voya/log.py src/voya/backup.py src/voya/preview.py src/voya/safety.py src/voya/db.py src/voya/metrics.py src/voya/ideas.py src/voya/providers scripts tests/test_m1_data.py tests/test_m2_cited_planner.py tests/test_m4_magic_link.py tests/test_p1_preview.py tests/test_p1_nyc.py tests/test_p1_a11y.py

typecheck:
	uv run mypy src/voya/cost src/voya/pricing src/voya/data src/voya/accounts src/voya/settings.py src/voya/log.py src/voya/backup.py src/voya/preview.py src/voya/safety.py src/voya/db.py src/voya/metrics.py src/voya/ideas.py src/voya/providers

policy:
	uv run python scripts/check_policy.py

citations:
	uv run python scripts/check_data_citations.py

traceability:
	uv run python scripts/check_traceability.py

secrets:
	bash scripts/check_secrets.sh

examples:
	uv run python scripts/validate_examples.py

eval:
	uv run python -c "print('eval stub: run golden trips in artifacts/evals/ (M6)')"

trace:
	uv run python -m voya.obs list

backup:
	uv run python -m voya.backup

.PHONY: run test verify sync lint typecheck policy citations traceability secrets examples eval trace backup
