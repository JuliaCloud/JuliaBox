worker_processes  2;
daemon off;
error_log logs/error.log warn;
user juser juser;

events {
    worker_connections 1024;
}

http {
    access_log off;
    resolver 8.8.8.8 8.8.4.4;

    # cache connection check results to speed up proxy (used by router.lua)
    lua_shared_dict connchk 10M;

    server {
        listen 80;

        # allow larger uploads
        client_body_buffer_size 10M;
        
        # To enable SSL on nginx uncomment and configure the following lines
        # We enable TLS, but not SSLv2/SSLv3 which is weak and should no longer be used and disable all weak ciphers.
        # Provide full path to certificate bundle (ssl-bundle.crt) and private key (juliabox.key). Rename as appropriate.
        # All HTTP traffic is redirected to HTTPS
        
        #listen 443 default_server ssl;

        #ssl_certificate        ssl-bundle.crt;
        #ssl_certificate_key    juliabox.key;
        
        #ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
        #ssl_ciphers ALL:!aNULL:!ADH:!eNULL:!LOW:!EXP:RC4+RSA:+HIGH:+MEDIUM;

        #if ($http_x_forwarded_proto = 'http') {
        #    return 302 https://$host$request_uri;
        #}

        #if ($scheme = http) {
        #    return 302 https://$host$request_uri;
        #}

        root www;

        set $SESSKEY '$$SESSKEY';
        client_max_body_size 20M;
        
        location /favicon.ico {
            include    mime.types;
        }

        location /assets/ {
            include    mime.types;
        }
        
        location /timedout.html {
        	internal;
        }
        
        error_page 502 /timedout.html;

        location = / {
            include jbox_router.incl;
        }

        location ~ "/(jbox|jci_)+[a-zA-Z0-9_\-]{1,50}/.*" {
            include jbox_router.incl;
        }

        location / {
            include jbox_router.incl;

            # WebSocket support (nginx 1.4)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout  600;
        }
    }
}