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
