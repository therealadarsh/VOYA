run:
	uv run uvicorn voya.api:app --reload --port 8000

test:
	uv run pytest -q -p no:warnings

trace:
	uv run python -m voya.obs list

.PHONY: run test trace
