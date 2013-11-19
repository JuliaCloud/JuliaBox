dofile(ngx.config.prefix() .. "lua/setupreq.lua")
local cjson = require "cjson";

local sessname = ngx.var.cookie_sessname
local delete_all_inactive = false
local delete_all = false
local delete_id = ''
local admin_user = false

local args = ngx.req.get_uri_args()
for key, val in pairs(args) do
    if key == "delete_all_inactive" then
        delete_all_inactive = true
        break
    elseif key == "delete_all" then
        delete_all = true
        break
    elseif key == "delete_id" then
        delete_id = val
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
elseif not (delete_id == '') then 
    kill_container(delete_id)
    delete_container(delete_id)
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
    
    local table_header = '<table border="1">  <tr><th>Id</th><th>Status</th><th>Name</th><th>Action</th></tr>'
    local active_containers = '<h3> Active containers </h3>' .. table_header
    local inactive_containers = '<h3> Inactive containers </h3><table border="1">' .. table_header
    
    local json = get_all_containers()
    for i,c in pairs(json) do
        local html_row = '<tr><td>'.. string.sub(c.Id, 0, 12) .. '...' .. '</td>'
        html_row = html_row .. '<td>'.. c.Status .. '</td>'
        html_row = html_row .. '<td>'.. c.Names[1]  .. '</td>'
        html_row = html_row .. '<td><a href="/hostadmin/?delete_id='.. c.Id .. '">Delete</a></td></tr>'
        
        if (c.Ports == cjson.null) then 
            inactive_containers = inactive_containers .. html_row
        else
            active_containers = active_containers  .. html_row
        end
    end    

    active_containers = active_containers .. '</table>'
    inactive_containers = inactive_containers .. '</table>'
    
    out = string.gsub(out, "$$ACTIVE_CONTAINERS", active_containers)
    out = string.gsub(out, "$$INACTIVE_CONTAINERS", inactive_containers)

else
    out = string.gsub(out, "$$STANDARD_LINKS", "Coming soon...")
    out = string.gsub(out, "$$ACTIVE_CONTAINERS", "")
    out = string.gsub(out, "$$INACTIVE_CONTAINERS", "")
end    


ngx.say(out)

return