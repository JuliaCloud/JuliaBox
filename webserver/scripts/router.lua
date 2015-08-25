-- router.lua
local M = {
    _VERSION = '0.01',
}

ngx.log(ngx.DEBUG, "juliabox.router.lua initialized.\npackage path:\n" .. package.path..'\n'..package.cpath)

local socketM = require "socket"
local httpM  = require "resty.http"
local cjson = require "cjson"

local local_hostname = socketM.dns.gethostname()
local local_ipaddr = socketM.dns.toip(local_hostname)
local json = cjson.new()

local key = ngx.var.SESSKEY

local api_refreshed_marker = " refreshed "
local api_refreshing_marker = " refreshing "
local api_pref_inst = " preferred "

local apimgr_port = 8887
local sessmgr_port = 8888

function M.unquote(s)
    if s ~= nil and s:find'^"' then
        return s:sub(2,-2)
    end
    return s
end

function M.is_valid_auth()
    local is_valid = false
    local succ, src, authjson = pcall(function()
        local auth = M.unquote(ngx.var.cookie_jb_auth)
        auth = ngx.decode_base64(auth)
        auth = json.decode(auth)
        return auth["u"] .. auth["t"], auth
    end)
    if succ then
        local digest = ngx.hmac_sha1(key, src)
        local b64 = ngx.encode_base64(digest)
        is_valid = (b64 == authjson["x"])
    else
        ngx.log(ngx.WARN, "Exception parsing auth " .. (src or ""))
    end
    return is_valid, authjson
end

function M.is_valid_session()
    local is_valid = false
    local succ, src, sessjson = pcall(function()
        local sess = M.unquote(ngx.var.cookie_jb_sess)
        sess = ngx.decode_base64(sess)
        sess = json.decode(sess)
        return (sess["c"] .. sess["i"] .. sess["t"]), sess
    end)
    if succ then
        local digest = ngx.hmac_sha1(key, src)
        local b64 = ngx.encode_base64(digest)
        is_valid = (b64 == sessjson["x"])
    else
        ngx.log(ngx.WARN, "Exception parsing session " .. (src or ""))
    end

    if is_valid == false then
        ngx.log(ngx.WARN, "invalid session")
    end
    return is_valid, sessjson
end

function M.get_authsig()
    local is_valid, authjson = M.is_valid_auth()
    return is_valid and authjson["x"] or ""
end

function M.rewrite_uri()
    local uri = ngx.var.uri
    local match

    ngx.log(ngx.DEBUG, "checking whether to rewrite uri: " .. uri)
    match = ngx.re.match(uri, "^/jci_[a-zA-Z0-9_\\-]{1,50}/(.*)")

    if match then
        local rewriteuri = "/" .. (match[1] or "")
        ngx.req.set_uri(rewriteuri, false)
        ngx.log(ngx.DEBUG, "rewrote uri to: " .. rewriteuri)
        return
    end
end

function M.set_forward_addr(desired_port, force_scheme, force_port)
    local desired_host = ngx.var.cookie_jb_iid
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

function M.refresh_apiloc(apiloc)
    -- set a marker to indicate refresh is triggered
    apiloc:set(api_refreshing_marker, "", 1*20)

    local rand = tostring(math.random(0,10))
    local digest = ngx.hmac_sha1(key, rand)
    local b64 = ngx.encode_base64(digest)
    local url = "http://127.0.0.1:" .. tostring(apimgr_port) .. "/?key=" .. rand .. "&sign=" .. ngx.escape_uri(b64)

    local httpc = httpM.new()
    httpc:set_timeout(5000)

    local res, err = httpc:request_uri(url, {
        method = "GET"
    })
    if err or not res then
        ngx.log(ngx.WARN, "error getting apiloc")
        return false
    end

    local apilocjson = json.decode(res.body)
    for api_collection,locs in pairs(apilocjson) do
        -- cache status for 2 minutes
        apiloc:set(api_collection, locs, 2*60)
        ngx.log(ngx.DEBUG, "api_collection " .. api_collection .. ": " .. tostring(locs))
    end
    -- set a marker to indicate if refresh is required
    apiloc:set(api_refreshed_marker, "", 1*60)
    return true
end

function M.get_apiloc(api_collection)
    local apiloc = ngx.shared.apiloc
    if not apiloc:get(api_refreshed_marker) and not apiloc:get(api_refreshing_marker) then
        M.refresh_apiloc(apiloc)
    end

    local api_hosts = apiloc:get(api_collection)
    local outgoing_host = "127.0.0.1"
    if api_hosts and #api_hosts then
        outgoing_host = api_hosts[math.random(#api_hosts)]
    else
        api_hosts = apiloc:get(api_pref_inst)
        if api_hosts and #api_hosts then
            outgoing_host = api_hosts[math.random(#api_hosts)]
        end
    end

    if (outgoing_host == "localhost") or (outgoing_host == nil) or (outgoing_host == local_hostname) or (outgoing_host == local_ipaddr) then
        outgoing_host = "127.0.0.1"
    end
    return outgoing_host
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
    local is_valid, sessjson = M.is_valid_session()
    if is_valid == false then
        ngx.say("Signature mismatch")
        ngx.exit(ngx.HTTP_FORBIDDEN)
    end
    return sessjson
end

function M.get_validated_port(sessjson, portname)
    local is_valid = false
    local succ, src, portjson = pcall(function()
        local portcookie = M.unquote(ngx.var["cookie_jp_" .. portname])
        portcookie = ngx.decode_base64(portcookie)
        portcookie = json.decode(portcookie)
        local authsig = M.get_authsig()
        local sesssig = sessjson["x"]
        return authsig .. sesssig .. portname .. portcookie["p"], portcookie
    end)

    if succ then
        local digest = ngx.hmac_sha1(key, src)
        local b64 = ngx.encode_base64(digest)
        is_valid = (b64 == portjson["x"])
    else
        ngx.log(ngx.WARN, "Exception parsing port " .. portname .. ". Error: " .. (src or ""))
    end
    return is_valid and portjson["p"] or ""
end

function M.jbox_route()
    local uri = ngx.var.uri
    local localforward

    -- route to juliabox container manager
    if (uri == "/") or ngx.re.match(uri, "^/jbox[a-zA-Z0-9_\\-]{1,50}/.*") then
        M.set_forward_addr(sessmgr_port, "http", sessmgr_port)
        if (uri == "/") or ngx.re.match(uri, "/jboxauth/.+") then
            ngx.var.jbox_forward_addr = M.check_forward_addr(ngx.var.jbox_forward_addr, "http://127.0.0.1:" .. tostring(sessmgr_port))
        elseif not ngx.re.match(uri, "/jboxcors/.*") then
            M.forbid_invalid_session()
        end
        ngx.log(ngx.DEBUG, "final forward_addr: " .. ngx.var.jbox_forward_addr)
        return
    end

    local match = ngx.re.match(uri, "^/jci_([a-zA-Z0-9_\\-]{1,50})/.*")
    if match then
        local sessjson = M.forbid_invalid_session()
        local portname = match[1]
        local portnum = M.get_validated_port(sessjson, portname)
        if portnum == "" then
            ngx.say("Invalid/no port specified for " .. portname)
            ngx.exit(ngx.HTTP_FORBIDDEN)
        end

        localforward = M.set_forward_addr(portnum, nil, nil)
        M.delay_till_available(ngx.var.jbox_forward_addr, "/")
        if localforward then M.rewrite_uri() end
        ngx.var.jbox_forward_addr = ngx.var.jbox_forward_addr .. ngx.var.uri .. (ngx.var.is_args or "") .. (ngx.var.query_string or "")
        ngx.log(ngx.DEBUG, "final forward_addr: " .. ngx.var.jbox_forward_addr)
        return
    end

    -- all others
    local sessjson = M.forbid_invalid_session()
    local portnum = M.get_validated_port(sessjson, "nb")
    if portnum == "" then
        ngx.say("Invalid/no port specified for nb")
        ngx.exit(ngx.HTTP_FORBIDDEN)
    end
    M.set_forward_addr(portnum, nil, nil)
    ngx.log(ngx.DEBUG, "final websock forward_addr: " .. ngx.var.jbox_forward_addr)
    return
end

function M.api_route()
    local uri = ngx.var.uri
    local match = ngx.re.match(uri, "^/([a-zA-Z0-9_\\-]{1,50})/([a-zA-Z0-9_][^/]*)/.*")
    if #match ~= 2 then
        ngx.say("Invalid URL")
        ngx.exit(ngx.HTTP_FORBIDDEN)
    end

    local api_collection = match[1]
    local apiloc = M.get_apiloc(api_collection)

    local outgoing = "http://" .. apiloc .. ":" .. tostring(apimgr_port) .. ngx.var.uri .. (ngx.var.is_args or "") .. (ngx.var.query_string or "")
    ngx.var.jbox_forward_addr = outgoing
    ngx.log(ngx.DEBUG, "api destination set to: " .. outgoing)
end

return M