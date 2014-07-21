worker_processes  2;
error_log logs/error.log warn;
user $$NGINX_USER $$NGINX_USER; 

events {
    worker_connections 1024;
}


http {
    resolver 8.8.8.8 8.8.4.4;
    server {
        listen 80;
        root www;

        set $SESSKEY '$$SESSKEY';
        
        location /favicon.ico {
            include    mime.types;
        }

# On the host, all locations will be specified explictly, i.e, with an "="
# Everything else will be proxied to the appropriate container....
# Cookie data will be used to identify the container for a session
        
        location = / {
            proxy_pass          http://localhost:8888;
            proxy_set_header    Host            $host;
            proxy_set_header    X-Real-IP       $remote_addr;
            proxy_set_header    X-Forwarded-for $remote_addr;        
        }        

        location ~ \/(hostlaunchipnb|hostadmin|ping)+\/  {
            proxy_pass          http://localhost:8888;
            proxy_set_header    Host            $host;
            proxy_set_header    X-Real-IP       $remote_addr;
            proxy_set_header    X-Forwarded-for $remote_addr;        
        }        
        

# container locations

# file upload and listing....

        location /hostipnbupl/ {
            access_by_lua_file 'lua/validate.lua';
        
            rewrite /hostipnbupl/(.+) /$1 break;
            
            proxy_pass http://127.0.0.1:$cookie_hostupl;
            
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }


# landing page
        location = /hostipnbsession/ {
            # wait for n seconds for the container's ipnb listener to be ready...
            
            access_by_lua '
                dofile(ngx.config.prefix() .. "lua/validate.lua")
                
                local http  = require "resty.http.simple"
                local n = 20
                local hostipnbport = ngx.var.cookie_hostipnb
                local opts = {}
                opts.path = "/"

                while (n > 0) do
                    local res, err = http.request("127.0.0.1", hostipnbport, opts)
                    if not res then
                        ngx.sleep(1.0)
                    else
                        return
                    end
                    n = n - 1
                end
                return
            ';
        
            proxy_pass http://127.0.0.1:$cookie_hostipnb/;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location /assets/ {
            include    mime.types;
        }

# everything else        
        location / {
            access_by_lua_file 'lua/validate.lua';
            
            proxy_pass http://127.0.0.1:$cookie_hostipnb;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            # WebSocket support (nginx 1.4)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
    }
}

