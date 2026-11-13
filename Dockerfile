FROM python:3.12-slim

RUN useradd --create-home --uid 10001 voya
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY data ./data
COPY README.md ./

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev \
    && mkdir -p /data \
    && chown -R voya:voya /app /data

ENV VOYA_ENV=production \
    VOYA_DEV_SIGNIN=0 \
    VOYA_DATA_DIR=/data \
    VOYA_LOG_FORMAT=json \
    UV_NO_SYNC=1

VOLUME /data
USER voya
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

CMD [".venv/bin/uvicorn", "voya.api:app", "--host", "0.0.0.0", "--port", "8000"]
