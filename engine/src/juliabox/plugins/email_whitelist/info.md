# Email whitelist plugin

Post-auth plugin to check if an email address used by the user matches a whitelisted pattern. The procedure is as follows:

1. Verify the `user_id` against the whitelist and allow the user if it matches
2. Check if the user has a verified alternate email, and if so allow access
2. If not, ask the user for an additional email address
3. Generate a random secret and email it to this address, embedded in a weblink
4. Upon clicking the link in the email, the address is verified and the user is directed to the login page
5. From now step 2 will succeed automatically upon successful authentication

The plugin creates a new database table `jbox_email_verify` to store the verified email addresses. It also requires a configured plugin for sending email, and a config entry `email_whitelist` with a list of domains or email addresses in `allowed_addresses`. It checks that the given email address ends with the given pattern, ignoring case. This allows whitelisting either domains or individual addresses.

Example config:

```
{
#... other config as needed ...
"email_whitelist": {
  "allowed_addresses": [
    "julia.org",
    "user@some.com"
  ]
},
"user_activation": {
    "sender": "email@fromaddress.com",
    "sender_password": "",
    "smtp_url": "smtp.mydomain.com",
    "smtp_port_no": 587,
    "max_24hrs": 100,
    "max_rate_per_sec": 1
},
"plugins": [
    #... other plugins as necessary ...
    "juliabox.plugins.email_whitelist",
    "juliabox.plugins.sendmail_smtp"
]
}
```
