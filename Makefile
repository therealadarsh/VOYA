RUN ?= uv run

LINT_PATHS := src/voya scripts tests
TYPE_PATHS := src/voya

.PHONY: help run test verify e2e migrate sync lint typecheck policy citations traceability secrets examples eval trace backup

help:
	@echo "Targets (use RUN= with snakeenv; default RUN=uv run for CI):"
	@echo "  run          – dev server on :8000 (needs uv or snakeenv)"
	@echo "  test         – pytest (123 passed, 2 skipped typical)"
	@echo "  verify       – lint, typecheck, test, policy, citations, …"
	@echo "  e2e          – install Chromium if needed, then tests/browser"
	@echo "  migrate      – apply Alembic migrations to the configured database"
	@echo "  sync         – uv sync --frozen (default RUN only)"
	@echo "  lint         – ruff check + format --check on LINT_PATHS"
	@echo "  typecheck    – mypy on TYPE_PATHS"
	@echo "  policy citations traceability secrets examples – repo checks"
	@echo "  eval trace backup – stubs / utilities"
	@echo "With RUN= empty, activate conda env snakeenv first or tools are not found."

run:
	$(RUN) uvicorn voya.api:app --reload --port 8000

test:
	$(RUN) pytest -q -p no:warnings

e2e:
	$(RUN) python -m playwright install chromium
	VOYA_BROWSER=1 $(RUN) pytest -q -p no:warnings tests/browser

migrate:
	$(RUN) alembic upgrade head

ifeq ($(RUN),uv run)
verify: sync lint typecheck test policy citations traceability secrets examples
else
verify: lint typecheck test policy citations traceability secrets examples
endif

sync:
	uv sync --frozen

lint:
	$(RUN) ruff check $(LINT_PATHS)
	$(RUN) ruff format --check $(LINT_PATHS)

typecheck:
	$(RUN) mypy $(TYPE_PATHS)

policy:
	$(RUN) python scripts/check_policy.py

citations:
	$(RUN) python scripts/check_data_citations.py

traceability:
	$(RUN) python scripts/check_traceability.py

secrets:
	bash scripts/check_secrets.sh

examples:
	$(RUN) python scripts/validate_examples.py

eval:
	$(RUN) python -c "print('eval stub: run golden trips in artifacts/evals/ (M6)')"

trace:
	$(RUN) python -m voya.obs list

backup:
	$(RUN) python -m voya.backup