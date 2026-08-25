# Django tutorial app に OpenTelemetry の Tracing を導入する

https://docs.djangoproject.com/en/6.1/intro/

Python 3.14 と package の管理には [uv](https://docs.astral.sh/uv/) を使用している。

Cloud Run で実行し、Cloud Trace に送ることを前提としている。


## PostgreSQL

以前は devbox で PostgreSQL を起動していたが、devbox の使用をやめたため各自で用意する。
container で起動する場合は例えば次のようにする。

```bash
docker run --rm -d --name mysite-db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16
```

[mysite/settings.py](./mysite/settings.py) は `DB_HOST`, `DB_PASSWORD` の環境変数を見るので

```bash
export DB_HOST=127.0.0.1
export DB_PASSWORD=postgres
```

Django で PostgreSQL サーバーの情報設定に `~/.pg_service.conf` (`PGSERVICEFILE`) を使用する場合は

settings.py で次のように指定して

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "OPTIONS": {
            "service": "my_service",
        },
    }
}
```

`~/.pg_service.conf` に次のように指定する

```ini
[my_service]
host=127.0.0.1
user=teraoka
dbname=mysite
port=5432
```

パスワードを設定する場合は `~/.pgpass` (`PGPASSFILE`) に書く

Unix Domain Socket を使う場合は path の最大長が 103 bytes であることに気をつける必要がある

```
LOG:  Unix-domain socket path "/very/long/path/to/the/socket/directory/.s.PGSQL.5432" is too long (maximum 103 bytes)
```

### psycopg2-binary はダメらしい

psycopg2 は source から build されるため libpq の header (Debian/Ubuntu では `libpq-dev`) が必要になるが、
psycopg2-binary ではなく psycopg2 を使用する

https://signoz.io/docs/instrumentation/django/#postgres-database-instrumentation

> psycopg2-binary is not supported by opentelemetry auto instrumentation
> libraries as it is not recommended for production use.
> Please use psycopg2 to see DB calls also in your trace data in SigNoz


## uv

Python 本体と package 管理には [uv](https://docs.astral.sh/uv/) を使用している。
uv 自体の install 方法は [公式 document](https://docs.astral.sh/uv/getting-started/installation/) を参照。

使用する Python の version は [.python-version](./.python-version) で 3.14 に固定してあり、
その version が手元になければ uv が自動で download する。

依存 package の install は次のコマンドで行う。project 内に `.venv` が作られ、
開発用 (pytest, ruff) の package も含めて [uv.lock](./uv.lock) のとおりに install される。

```bash
uv sync
```

`--no-dev` を付けると application の実行に必要な package のみが install される (Dockerfile ではこちらを使用している)。
`--locked` を付けると lock file の更新が必要な状態のときに失敗する (CI ではこちらを使用している)。

command の実行は `uv run` を使う。`.venv` を activate する必要はない。

```bash
uv run python manage.py migrate
```

package の追加や更新は次のようにする。

```bash
uv add 'some-package'          # 依存の追加
uv add --dev 'some-package'    # 開発用依存の追加
uv lock --upgrade              # lock file 内の package を最新に更新
```

psycopg2 は source から build されるため libpq の header (Debian/Ubuntu では `libpq-dev`) が必要になる。


## Test

test は [pytest](https://docs.pytest.org/) + [pytest-django](https://pytest-django.readthedocs.io/) で実行する。

```bash
uv run pytest
```

coverage を見る場合は

```bash
uv run pytest --cov --cov-report=term-missing
```

Django 標準の test runner でも実行できる。

```bash
DJANGO_SETTINGS_MODULE=mysite.settings_test uv run python manage.py test
```

test では PostgreSQL の代わりに in-memory の SQLite を使う ([mysite/settings_test.py](./mysite/settings_test.py))。
DB server を用意しなくても test が実行できるようにするためで、pytest は
[pyproject.toml](./pyproject.toml) の `DJANGO_SETTINGS_MODULE` でこの設定 module を読み込む。

外部への HTTP request (`https://httpbin.org/delay/2`) や `time.sleep()` は trace を分かりやすく
するために view に入れてあるものなので、test では mock している。


## Lint, Format

[ruff](https://docs.astral.sh/ruff/) を linter 兼 formatter として使用している。設定は
[pyproject.toml](./pyproject.toml) の `[tool.ruff]` にある。

```bash
uv run ruff check .          # lint
uv run ruff check --fix .    # lint (自動修正)
uv run ruff format .         # format
uv run ruff format --check . # format 確認のみ
```

lint と test は [.github/workflows/python.yaml](./.github/workflows/python.yaml) で
pull request と main への push の際に実行される。


## daphne を使って実行

事情により daphne が使用されているので

```
uv run python -m daphne -b 0.0.0.0 -p 8000 mysite.asgi:application
```

asgi なので [opentelemetry-instrumentation-asgi](https://pypi.org/project/opentelemetry-instrumentation-asgi/) が必要。

[OpenTelemetry ASGI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/asgi/asgi.html)
おや？ OpenTelemetryMiddleware という便利なものがあったのか。TODO


## 参考情報

- https://opentelemetry.io/
- https://github.com/GoogleCloudPlatform/opentelemetry-operations-python
- https://google-cloud-opentelemetry.readthedocs.io/en/latest/index.html
- https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/django/django.html
- https://github.com/GoogleCloudPlatform/opentelemetry-operator-sample
- https://signoz.io/docs/instrumentation/django/
- https://cloud.google.com/run/docs/container-contract
- [OpenTelemetryでWebシステムの処理を追跡しよう - DjangoCongress JP 2022](https://www.slideshare.net/shimizukawa/lets-trace-web-system-processes-with-opentelemetry-djangocongress-jp-2022) (slideshare)
- https://github.com/shimizukawa/try-otel/blob/20221112-djangocongressjp2022/backend/config/otel.py

[Cloud Trace Exporter Example](https://google-cloud-opentelemetry.readthedocs.io/en/latest/examples/cloud_trace_exporter/README.html) は import の指定が間違っているような気がする。


## TODO

- terraform
