-- router.lua
local M = {
    _VERSION = '0.01',
}

ngx.log(ngx.DEBUG, "juliabox.router.lua initialized.\npackage path:\n" .. package.path..'\n'..package.cpath)

local socketM = require "socket"
local httpM  = require "resty.http"

local local_hostname = socketM.dns.gethostname()
local local_ipaddr = socketM.dns.toip(local_hostname)

local key = ngx.var.SESSKEY
local cookienames = {"hostipnb", "hostshell", "hostupload", "instance_id", "sessname"}
table.sort(cookienames)

function M.unquote(s)
    if s ~= nil and s:find'^"' then
        return s:sub(2,-2)
    end
    return s
end

function M.is_valid_session()
    local toks = {}
    for i,cname in ipairs(cookienames) do
        local varname = "cookie_" .. cname
        local cval = ngx.var[varname]
        if cval ~= nil then
            table.insert(toks, cname)
            table.insert(toks, M.unquote(cval))
        end
    end
    local src = table.concat(toks, "_")
    local digest = ngx.hmac_sha1(key, src)
    local b64 = ngx.encode_base64(digest)
    local is_valid = (b64 == M.unquote(ngx.var.cookie_sign))

    if is_valid == false then
        ngx.log(ngx.WARN, "invalid session b64(" .. src .. ") = " .. b64 .. " != " .. (M.unquote(ngx.var.cookie_sign) or ""))
    end
    return is_valid
end

function M.rewrite_uri()
    local uri = ngx.var.uri
    local match

    ngx.log(ngx.DEBUG, "checking whether to rewrite uri: " .. uri)
    match = ngx.re.match(uri, "^/hostupload/(.*)") or ngx.re.match(uri, "^/hostshell/(.*)") or ngx.re.match(uri, "^/hostipnbsession/(.*)")

    if match then
        local rewriteuri = "/" .. (match[1] or "")
        ngx.req.set_uri(rewriteuri, false)
        ngx.log(ngx.DEBUG, "rewrote uri to: " .. rewriteuri)
        return
    end
end

function M.set_forward_addr(desired_port, force_scheme, force_port)
    local desired_host = ngx.var.cookie_instance_id
    local incoming_port = ngx.var.server_port
    local incoming_scheme = ngx.var.scheme

    local outgoing_host = desired_host
    local outgoing_port = incoming_port
    local outgoing_scheme = incoming_scheme
    local localforward = false

    ngx.log(ngx.DEBUG, incoming_scheme .. "://(" .. local_hostname .. "|" .. local_ipaddr .. "):" .. incoming_port .. " => desired " .. (desired_host or "") .. ":" .. desired_port)
    if (desired_host == "localhost") or (desired_host == "127.0.0.1") or (desired_host == nil) or (desired_host == local_hostname) or (desired_host == local_ipaddr) then
        -- send to localhost if:
        -- - host not set
        -- - already pointing to local hostname/ipaddress
        outgoing_host = "127.0.0.1"
        outgoing_port = desired_port
        outgoing_scheme = "http"
        localforward = true
    end

    if force_scheme ~= nil then
        outgoing_scheme = force_scheme
    end
    if force_port ~= nil then
        outgoing_port = force_port
        localforward = true
    end

    local outgoing = outgoing_scheme .. "://" .. outgoing_host .. ":" .. outgoing_port
    ngx.var.jbox_forward_addr = outgoing
    ngx.log(ngx.DEBUG, "destination set to: " .. outgoing .. " localforward:" .. tostring(localforward))
    return localforward
end

function M.is_accessible(url)
    local urlhash = "u" .. ngx.md5(url)
    local connchk = ngx.shared.connchk

    if connchk:get(urlhash) then
        ngx.log(ngx.DEBUG, "validated from cache: " .. url)
        return true
    end

    local httpc = httpM.new()
    httpc:set_timeout(1000)

    local res, err = httpc:request_uri(url, {
        method = "GET"
    })

    if res then
        -- cache status for 2 minutes
        connchk:set(urlhash, true, 2*60)
        return true
    end
    ngx.log(ngx.DEBUG, "not accessible " .. url .. " got error: " .. err)

    return false
end

function M.wait_till_accessible(url, n)
    ngx.log(ngx.DEBUG, "wait_till_accessible: " .. url)
    while (n > 0) do
        if M.is_accessible(url) then
            return true
        end
        ngx.sleep(1.0)
        n = n - 1
    end
    return false
end

function M.check_forward_addr(outgoing, replacement)
    if M.wait_till_accessible(outgoing, 2) then
        return outgoing
    end
    ngx.log(ngx.WARN, "replacing inaccessible forward address " .. outgoing .. " with " .. replacement)
    return replacement
end

function M.delay_till_available(outgoing, path)
    M.wait_till_accessible(outgoing .. path, 20)
    return
end

function M.forbid_invalid_session()
    if M.is_valid_session() == false then
        ngx.say("Signature mismatch")
        ngx.exit(ngx.HTTP_FORBIDDEN)
    end
end

function M.jbox_route()
    local match
    local uri = ngx.var.uri
    local localforward

    if (uri == "/") or (uri == "/hostlaunchipnb/") or ngx.re.match(uri, "/jboxauth/.+") then
        M.set_forward_addr(8888, "http", 8888)
        ngx.var.jbox_forward_addr = M.check_forward_addr(ngx.var.jbox_forward_addr, "http://127.0.0.1:8888")
        ngx.log(ngx.DEBUG, "final forward_addr: " .. ngx.var.jbox_forward_addr)
        return
    end

    if ngx.re.match(uri, "/(hostadmin|ping|cors|jboxplugin)+/") then
        M.set_forward_addr(8888, "http", 8888)
        ngx.log(ngx.DEBUG, "final forward_addr: " .. ngx.var.jbox_forward_addr)
        return
    end

    match = ngx.re.match(uri, "^/hostupload/.*")
    if match then
        M.forbid_invalid_session()
        localforward = M.set_forward_addr(ngx.var.cookie_hostupload, nil, nil)
        M.delay_till_available(ngx.var.jbox_forward_addr, "/ping")
        if localforward then M.rewrite_uri() end
        ngx.var.jbox_forward_addr = ngx.var.jbox_forward_addr .. ngx.var.uri .. (ngx.var.is_args or "") .. (ngx.var.query_string or "")
        ngx.log(ngx.DEBUG, "final forward_addr: " .. ngx.var.jbox_forward_addr)
        return
    end

    match = ngx.re.match(uri, "^/hostshell/.*")
    if match then
        M.forbid_invalid_session()
        localforward = M.set_forward_addr(ngx.var.cookie_hostshell, nil, nil)
        M.delay_till_available(ngx.var.jbox_forward_addr, "/")
        if localforward then M.rewrite_uri() end
        ngx.var.jbox_forward_addr = ngx.var.jbox_forward_addr .. ngx.var.uri .. (ngx.var.is_args or "") .. (ngx.var.query_string or "")
        ngx.log(ngx.DEBUG, "final forward_addr: " .. ngx.var.jbox_forward_addr)
        return
    end

    if uri == "/hostipnbsession/" then
        M.forbid_invalid_session()
        localforward = M.set_forward_addr(ngx.var.cookie_hostipnb, nil, nil)
        M.delay_till_available(ngx.var.jbox_forward_addr, "/")
        if localforward then M.rewrite_uri() end
        ngx.var.jbox_forward_addr = ngx.var.jbox_forward_addr .. ngx.var.uri .. (ngx.var.is_args or "") .. (ngx.var.query_string or "")
        ngx.log(ngx.DEBUG, "final forward_addr: " .. ngx.var.jbox_forward_addr)
        return
    end

    -- all others
    M.forbid_invalid_session()
    M.set_forward_addr(ngx.var.cookie_hostipnb, nil, nil)
    ngx.log(ngx.DEBUG, "final websock forward_addr: " .. ngx.var.jbox_forward_addr)
    return
end

return M