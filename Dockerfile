FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY data ./data
RUN pip install uv && uv sync --frozen --no-dev
# Optional: copy React build to web/dist and set VOYA_UI=react
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "voya.api:app", "--host", "0.0.0.0", "--port", "8000"]
