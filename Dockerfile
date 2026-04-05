FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 5000

CMD ["uv", "run", "gunicorn", "run:app", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2"]
