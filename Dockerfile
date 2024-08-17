## Builder ##
FROM python:3.12-slim as builder

RUN pip install poetry==1.8.2

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-root --no-cache --no-interaction --only=main

## Runtime ##
FROM python:3.12-slim as runtime

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY src/*.py src/
COPY src/database/*.py src/database/
COPY src/notification/*.py src/notification/

COPY config/* config/

EXPOSE 8000
CMD ["python", "-u", "-m", "src.main"]
