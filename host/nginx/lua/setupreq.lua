local cjson = require "cjson";
local http  = require "resty.http.simple"

function trim(s)
    return s:find'^%s*$' and '' or s:match'^%s*(.*%S)'
end

function lognexit(s, ...)
    ngx.log(ngx.ERR, s, ...)
    ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

function do_docker_req(uri, ...)
    local method, body, headers = ...
    
    local opts = {}
    opts.path = "/docker" .. uri
    if type(method) == "string" then
        opts.method = method
    end

    if type(body) == "string" then
        opts.body = body
    end

    if type(headers) == "table" then
        opts.headers = headers
    end
    
    
    local res, err = http.request("127.0.0.1", 81, opts)
    if not res then
        lognexit("http failure: ", err)
    end

    if ((res.status < 200) or (res.status >= 300)) then
        lognexit("Query returned a non-200 response: " .. res.status)
    end
    
    if (type(res.body) == "string") and (#res.body > 0) then
--        ngx.say(opts.path .. "\n" .. res.body .. "\n\n\n\n")
        local json = cjson.decode(res.body)
        return json, res.status
    end
    
    return nil, res.status
end    
        
    

function get_all_containers()
    return do_docker_req("/containers/json?all=1")
end

function get_running_containers()
    return do_docker_req("/containers/json")
end

function is_container_running(name)
    local json = get_running_containers()
    
    local nname = "/" .. name
    for i,c in pairs(json) do
        if c.Names[1] == nname then
            return true, c
        end    
    end    
    return false    
end

function is_container(name)
    local json = get_all_containers()
    
    local nname = "/" .. name
    for i,c in pairs(json) do
        if c.Names[1] == nname then
            return true, c
        end    
    end    
    return false    
end


function get_container_id(name)
    local json = get_all_containers()
    
    local nname = "/" .. name
    for i,c in pairs(json) do
        if c.Names[1] == nname then
            return c.Id, c
        end    
    end    
    return
end

function kill_container(id)
    local _x, httpcode = do_docker_req("/containers/" .. id .. "/kill", "POST")
    if not (httpcode == 204)  then
        lognexit("Unable to kill container : ", id)
    end
end    

function delete_container(id)
    local _x, httpcode = do_docker_req("/containers/" .. id .. "?v=1", "DELETE")
    if not (httpcode == 204)  then
        lognexit("Unable to delete container : ", id)
    end
end    

function get_container_ports_by_id(id)
    resp, httpcode = do_docker_req("/containers/" .. id .. "/json", "GET")
    if not (httpcode == 200) then
        lognexit("Error inspecting container : ", httpcode)
    end
    
    -- get the mapped ports
    return resp["NetworkSettings"]["Ports"]["8000/tcp"][1]["HostPort"], resp["NetworkSettings"]["Ports"]["8998/tcp"][1]["HostPort"]
end

function create_new_container(name)
    -- create container
    local cspec = "{\"PortSpecs\":[\"8998\", \"8000\"], \"Image\":\"ijulia\", \"AttachStdout\":false, \"AttachStderr\":false}"
    local headers = {}
    headers["Content-Type"] = "application/json"
    
    local resp, httpcode = do_docker_req("/containers/create?name=" .. name, "POST", cspec, headers)
    if not (httpcode == 201) then
        lognexit("Error creating container : ", httpcode)
    end
    
    local id = resp.Id
    
    -- start it
    resp, httpcode = do_docker_req("/containers/" .. id .. "/start", "POST", "{\"PublishAllPorts\":true}", headers)
    if not (httpcode == 204) then
        lognexit("Error starting container : ", httpcode)
    end
    
    return id
end


function launch_container(name, clear_old_sess)
    local iscont, c = is_container(name)
    
    local id = ""
    
    -- kill the container 
    -- if it exists and clear_old_sess
    -- if it exists and is not in a running state
    
    if iscont and (c.Ports == cjson.null) then
        clear_old_sess = true
    end
    
    if (iscont and clear_old_sess) then
        kill_container(c.Id)
        delete_container(c.Id)
    end
    
    if (not iscont) or clear_old_sess then
        id = create_new_container(name)
    else
        id = c.Id
    end
    
    local uplport, ipnbport = get_container_ports_by_id(id)
    if not ipnbport then
      return
    end
    
    return id, uplport, ipnbport
end


function get_container_ports_by_name(name)
    local iscont, c = is_container(name)
    
    if not iscont then
        lognexit("ERROR: Could not find session : ", name)
    end
    
    return get_container_ports_by_id(c.Id)
end




