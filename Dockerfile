FROM python:3.13 AS builder

RUN pip install poetry~=1.8.3

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN --mount=type=cache,target=$POETRY_CACHE_DIR
RUN poetry install --no-root

COPY cheezen ./cheezen

FROM python:3.13-slim AS runtime

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY cheezen ./cheezen
COPY logging.yaml ./logging.yaml

ENTRYPOINT ["python", "-m", "cheezen.main"]