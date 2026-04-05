FROM python:3.13-slim

# Don't run as root in production
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN mkdir -p /home/appuser/.cache/uv && chown -R appuser:appuser /app /home/appuser
USER appuser

EXPOSE 5000

CMD ["uv", "run", "gunicorn", "run:app", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--access-logfile", "-"]
