dofile(ngx.config.prefix() .. "lua/setupreq.lua")
local cjson = require "cjson";

local sessname = ngx.var.cookie_sessname
local delete_all_inactive = false
local delete_all = false
local admin_user = false

local args = ngx.req.get_uri_args()
for key, val in pairs(args) do
    if key == "delete_all_inactive" then
        delete_all_inactive = true
        break
    elseif key == "delete_all" then
        delete_all = true
        break
    end
end

sessname = trim(sessname)
if sessname == "" then
    lognexit("ERROR : sessname not found ")
end

if sessname == ngx.var.admin_sessname then 
    admin_user = true
end


if delete_all_inactive or delete_all then
    local json = get_all_containers()
    local dockername = "/" .. sessname
    
    for i,c in pairs(json) do
        if not (dockername == c.Names[1]) then
            if delete_all or (c.Ports == cjson.null) then
                kill_container(c.Id)
                delete_container(c.Id)
            end
        end
    end    
end

-- return a web page with the sessionname placeholder replaced
local f, err = io.open(ngx.config.prefix() .. "www/ipnbadmin.tpl")
if f == nil then
    lognexit("ERROR: Unable to open IPNB template [", err, "]")
end
tpl = f:read("*a")
f:close()

out = string.gsub(tpl, "$$SESSNAME", sessname)
if admin_user then
    local std_links = '<a href="/hostadmin/">Refresh</a><br><br>'
    std_links = std_links .. '<a href="/hostadmin/?delete_all_inactive=1">Delete all inactive containers</a><br><br>'
    std_links = std_links .. '<a href="/hostadmin/?delete_all=1">Delete all containers</a><br><br>'
    out = string.gsub(out, "$$STANDARD_LINKS", std_links)
    
    local active_containers = '<h3> Active containers </h3>'
    local inactive_containers = '<h3> Inactive containers </h3>'
    
    local json = get_all_containers()
    for i,c in pairs(json) do
        if (c.Ports == cjson.null) then 
            inactive_containers = inactive_containers .. 'Id: ' .. c.Id .. ', Status : ' .. c.Status .. ', Name : ' .. c.Names[1]  .. '<br>'
        else
            active_containers = active_containers .. 'Id: ' .. c.Id .. ', Status : ' .. c.Status .. ', Name : ' .. c.Names[1]  .. '<br>'
        end
    end    
    
    out = string.gsub(out, "$$ACTIVE_CONTAINERS", active_containers)
    out = string.gsub(out, "$$INACTIVE_CONTAINERS", inactive_containers)

else
    out = string.gsub(out, "$$STANDARD_LINKS", "Coming soon...")
    out = string.gsub(out, "$$ACTIVE_CONTAINERS", "")
    out = string.gsub(out, "$$INACTIVE_CONTAINERS", "")
end    


ngx.say(out)

return