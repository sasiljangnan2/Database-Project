FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml constraints.txt ./
COPY app/ ./app/

RUN pip install --no-cache-dir -c constraints.txt . \
    && useradd --create-home --uid 10001 appuser

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
