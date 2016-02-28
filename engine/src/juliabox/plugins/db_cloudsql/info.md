# Google Cloud SQL

Pull the cloudsql proxy docker image:

```
> docker pull b.gcr.io/cloudsql-docker/gce-proxy
```

Add the following to `/jboxengine/conf/jbox.user`:

```
'db': {
    'user': 'username'
    'passwd': 'password'
    'unix_socket': '/cloudsql/<YOUR-PROJECT-ID>:<REGION-NAME>:<SQL-INSTANCE-NAME>',
    'db': 'JuliaBox'
}
```

Uncomment the `[program:cloudsqlproxy]` part of `host/supervisord.conf`.
