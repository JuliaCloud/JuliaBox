# Google Cloud Storage plugin

To use Google cloud storage requires an OAuth2.0 Service Account.  Fill in the following parametes in `/jboxengine/conf/jbox.user` :

```python
{
    # ...
    "backup_location" : "/jboxengine/data/backups",
    "plugins": [
        # ...
        "juliabox.plugins.bucket_gs",
    ],

    "google_oauth": {
        "key": "<the private key ID>",
        "secret": "<the private key>",
        "client_email": "<service account email>",
        "client_id": "<service account ID>",
    },

    "cloud_host": {
        # ...
        "backup_bucket": "<backup bucket name>",
        "status_bucket": "<status bucket name>",
    },
}
```
