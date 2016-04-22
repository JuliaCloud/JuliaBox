# SMTP plugin

Send mails using SMTP.  The following parameters must be added to `user_activation` in `jbox.user` in addition to `sender`, `mail_body` etc.

```
'user_activation': {
    ...,
    'sender_password': 'Password of the sender email address',
    'smtp_url': 'The URL of the SMTP server',
    'smtp_port_no': 'The SMTP port number',
    'max_24hrs': 'The maximum number of outgoing mails in a 24 hour time period',
    'max_rate_per_sec': 'The allowed rate of sending emails'
}
```