# Django tutorial

https://docs.djangoproject.com/en/4.1/intro/

[devbox](https://www.jetpack.io/devbox/docs/) の Python 3.11, PostgreSQL を使っている

direnv が使えるようになっていない場合は `devbox shell` を実行することで必要な環境変数がセットされる

PostgreSQL を起動させるには次のコマンドを実行する

```
devbox services start
```

PostgreSQL サーバーの情報は `~/.pg_service.conf` (`PGSERVICEFILE`) を使用している
パスワードを設定する場合は `~/.pgpass` (`PGPASSFILE`) に書く

```
$ cat ~/.pg_service.conf
[my_service]
host=/Users/teraoka/work/django-otel-cloud-trace/.devbox/virtenv/postgresql_14
user=teraoka
dbname=mysite
port=5432
```

Unix Domain Socket の path の最大長が 103 bytes なので気をつける必要がある

```
LOG:  Unix-domain socket path "/Users/teraoka/ghq/github.com/yteraoka/django-otel-cloud-trace/.devbox/virtenv/postgresql_14/.s.PGSQL.5432" is too long (maximum 103 bytes)
```

- https://pypi.org/project/opentelemetry-exporter-gcp-monitoring/
- https://pypi.org/project/opentelemetry-exporter-gcp-trace/
- https://pypi.org/project/opentelemetry-instrumentation-django/
- https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/django/django.html

```
pip install opentelemetry-sdk
pip install opentelemetry-instrumentation-django
pip install opentelemetry-exporter-gcp-trace
pip install opentelemetry-distro
```

して `manage.py` に追記する

```diff
diff --git a/mysite/manage.py b/mysite/manage.py
index a7da667..65fe5cb 100755
--- a/mysite/manage.py
+++ b/mysite/manage.py
@@ -3,10 +3,16 @@
 import os
 import sys

+from opentelemetry.instrumentation.django import DjangoInstrumentor
+

 def main():
     """Run administrative tasks."""
     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
+
+    # This call is what makes the Django application be instrumented
+    DjangoInstrumentor().instrument()
+
     try:
         from django.core.management import execute_from_command_line
     except ImportError as exc:
```

```
../venv/bin/opentelemetry-bootstrap -a install
```

を実行したら沢山 package がインストールされた

```diff
diff --git a/requirements.txt b/requirements.txt
index c92bece..518b1d1 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,4 +1,44 @@
 asgiref==3.6.0
+cachetools==5.3.0
+certifi==2022.12.7
+charset-normalizer==3.0.1
+Deprecated==1.2.13
 Django==4.1.7
+google-api-core==2.11.0
+google-auth==2.16.1
+google-cloud-trace==1.10.0
+googleapis-common-protos==1.58.0
+grpcio==1.51.3
+grpcio-status==1.51.3
+idna==3.4
+opentelemetry-api==1.16.0
+opentelemetry-distro==0.37b0
+opentelemetry-exporter-gcp-trace==1.4.0
+opentelemetry-instrumentation==0.37b0
+opentelemetry-instrumentation-asgi==0.37b0
+opentelemetry-instrumentation-aws-lambda==0.37b0
+opentelemetry-instrumentation-dbapi==0.37b0
+opentelemetry-instrumentation-django==0.37b0
+opentelemetry-instrumentation-grpc==0.37b0
+opentelemetry-instrumentation-logging==0.37b0
+opentelemetry-instrumentation-requests==0.37b0
+opentelemetry-instrumentation-sqlite3==0.37b0
+opentelemetry-instrumentation-urllib==0.37b0
+opentelemetry-instrumentation-urllib3==0.37b0
+opentelemetry-instrumentation-wsgi==0.37b0
+opentelemetry-propagator-aws-xray==1.0.1
+opentelemetry-sdk==1.16.0
+opentelemetry-semantic-conventions==0.37b0
+opentelemetry-util-http==0.37b0
+proto-plus==1.22.2
+protobuf==4.22.0
 psycopg2-binary==2.9.5
+pyasn1==0.4.8
+pyasn1-modules==0.2.8
+requests==2.28.2
+rsa==4.9
+six==1.16.0
 sqlparse==0.4.3
+typing_extensions==4.5.0
+urllib3==1.26.14
+wrapt==1.15.0
```

xray とか aws-lambda は不要そうだな

Django が main を2度読み込むのを防ぐために runserver に `--noreload` をつける必要がある

```
python manage.py runserver --noreload
```

ということでこうすれば良いのか？

```
opentelemetry-instrument --traces_exporter gcp_trace \
  --exporter_gcp_trace_project_id ${GOOGLE_PROJECT_ID} \
  python manage.py runserver --noreload
```

これはうまくいかなくて、 `mysite/opentelemetry_config.py` を設置して

```
python manage.py runserver --noreload
```

で起動させた。

不要 package を削っていく

psycopg2-binary はダメらしい

https://signoz.io/docs/instrumentation/django/#postgres-database-instrumentation

> psycopg2-binary is not supported by opentelemetry auto instrumentation
> libraries as it is not recommended for production use.
> Please use psycopg2 to see DB calls also in your trace data in SigNoz
