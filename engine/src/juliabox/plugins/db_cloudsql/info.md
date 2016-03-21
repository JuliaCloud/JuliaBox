# Google Cloud SQL

Uncomment the line `# configure_cloudsql` in `scripts/install/sys_install.sh` and run it.

Uncomment the block `[program:cloudsqlproxy]` from `host/supervisord.conf`.

Add the following to `/jboxengine/conf/jbox.user`:

```
'db': {
    'user': 'username'
    'passwd': 'password'
    'unix_socket': '/cloudsql/<YOUR-PROJECT-ID>:<REGION-NAME>:<SQL-INSTANCE-NAME>',
    'db': 'JuliaBox'
}
```