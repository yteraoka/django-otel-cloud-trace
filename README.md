# Django tutorial app に OpenTelemetry の Tracing を導入する

https://docs.djangoproject.com/en/4.1/intro/

[devbox](https://www.jetpack.io/devbox/docs/) の Python 3.10, PostgreSQL を使っている。

Cloud Run で実行し、Cloud Trace に送ることを前提としている。


## Devbox

開発には devbox を使用しているため、[devbox.json](./devbox.json) が配置してある。

[devbox](https://www.jetpack.io/devbox/) を install して `devbox shell` を実行することで python や poetry, PostgreSQL が使えるようになる。 (`direnv` 連携はしていない)
devbox shell から抜ける場合は exit か Ctrl-D.

```bash
devbox shell
```

PostgreSQL を起動させるには次のコマンドを実行する

```bash
devbox services start
```

Django で PostgreSQL サーバーの情報設定に `~/.pg_service.conf` (`PGSERVICEFILE`) を使用する場合は

settings.py で次のように指定して

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'service': 'my_service',
        }
    }
}
```

`~/.pg_service.conf` に次のように指定する

```ini
[my_service]
host=/Users/teraoka/work/django-otel-cloud-trace/.devbox/virtenv/postgresql_14
user=teraoka
dbname=mysite
port=5432
```

パスワードを設定する場合は `~/.pgpass` (`PGPASSFILE`) に書く

Unix Domain Socket の path の最大長が 103 bytes なので気をつける必要がある

```
LOG:  Unix-domain socket path "/Users/teraoka/ghq/github.com/yteraoka/django-otel-cloud-trace/.devbox/virtenv/postgresql_14/.s.PGSQL.5432" is too long (maximum 103 bytes)
```

### psycopg2-binary はダメらしい

devbox 環境でも psycopg2 のインストールは問題ないので psycopg2 を使用する

https://signoz.io/docs/instrumentation/django/#postgres-database-instrumentation

> psycopg2-binary is not supported by opentelemetry auto instrumentation
> libraries as it is not recommended for production use.
> Please use psycopg2 to see DB calls also in your trace data in SigNoz


## Poetry

package 管理には [poetry](https://python-poetry.org/) を使用している。poetry 自体は devbox でインストールしている。

`poetry config virtualenvs.in-project true` で project の directory 内に .venv を作るようにしている。


## daphne を使って実行

事情により daphne が使用されているので

```
poetry run python -m daphne -b 0.0.0.0 -p 8000 mysite.asgi:application
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
