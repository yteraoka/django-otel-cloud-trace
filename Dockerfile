FROM python:3.11.4 as builder

RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Don't buffer `stdout`
ENV PYTHONUNBUFFERED=1
# Don't create `.pyc` files
ENV PYTHONDONTWRITEBYTECODE=1

ENV POETRY_HOME /etc/poetry
ENV POETRY_VERSION 1.3.2

WORKDIR /code

COPY pyproject.toml poetry.lock ./

RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
 && chmod +x $POETRY_HOME/bin/poetry \
 && $POETRY_HOME/bin/poetry config virtualenvs.in-project true \
 && $POETRY_HOME/bin/poetry install --only main --no-root --no-interaction --no-ansi


FROM python:3.11.6-slim

RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --gid users --uid 1001 --create-home app

USER app

COPY --from=builder /code/.venv /code/.venv

WORKDIR /code
ENV PORT 8000
COPY . ./

CMD /code/.venv/bin/python -m daphne -b 0.0.0.0 -p $PORT mysite.asgi:application
