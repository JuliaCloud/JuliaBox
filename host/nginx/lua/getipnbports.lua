dofile(ngx.config.prefix() .. "lua/setupreq.lua")

local args = ngx.req.get_uri_args()
if not args then
    lognexit( "ERROR : Failed to get query params: ", err)
end
local ipnbport = 0
local uplport = 0
local sessname = ""
for key, val in pairs(args) do
    if key == "sessname" then
        sessname = val
    end
end

sessname = trim(sessname)

if sessname == "" then
    lognexit("ERROR : Session name not defined.")
end

uplport, ipnbport = get_container_ports_by_name(sessname)
ngx.log(ngx.ERR, "Ports : ", uplport, ipnbport)







