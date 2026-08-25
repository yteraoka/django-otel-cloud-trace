FROM python:3.14.7 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Don't buffer `stdout`
ENV PYTHONUNBUFFERED=1
# Don't create `.pyc` files
ENV PYTHONDONTWRITEBYTECODE=1

# Create the virtualenv at /code/.venv and use the interpreter of the base image
# (psycopg2 is built from source, the header files are in this image already)
ENV UV_PROJECT_ENVIRONMENT=/code/.venv
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_LINK_MODE=copy

WORKDIR /code

COPY pyproject.toml uv.lock .python-version ./

RUN uv sync --locked --no-dev


FROM python:3.14.7-slim

# application は /code/.venv から実行するので pip は不要。
# pip が vendoring している library (msgpack, setuptools) の脆弱性が
# image scan で報告されるため削除しておく。
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip uninstall --yes pip \
 && useradd --gid users --uid 1001 --create-home app

USER app

COPY --from=builder /code/.venv /code/.venv

WORKDIR /code
ENV PORT=8000
COPY . ./

CMD /code/.venv/bin/python -m daphne -b 0.0.0.0 -p $PORT mysite.asgi:application
