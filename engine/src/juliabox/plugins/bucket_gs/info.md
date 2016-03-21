# Google Cloud Storage plugin

Fill in the following parametes in `/jboxengine/conf/jbox.user` :

```python
{
    # ...
    "backup_location" : "/jboxengine/data/backups",
    "plugins": [
        # ...
        "juliabox.plugins.bucket_gs",
    ],

    "cloud_host": {
        # ...
        "backup_bucket": "<backup bucket name>",
        "status_bucket": "<status bucket name>",
    },
}
```
