dofile(ngx.config.prefix() .. "lua/setupreq.lua")

ngx.req.read_body()
local args = ngx.req.get_post_args()
if not args then
    lognexit("Failed to get post args: ", err)
end
local sessname = ""
local clear_old_sess = false

for key, val in pairs(args) do
    if key == "sessname" then
        sessname = val
    elseif key == "clear_old_sess" then
        clear_old_sess = true
    end
end




sessname = trim(sessname)
if sessname == "" then
    lognexit("ERROR : sessname not found ")
end

local id, uplport, ipnbport = launch_container(sessname, clear_old_sess)
if not ipnbport then
    lognexit("ERROR : Unable to launch container")
end

-- return a web page with the sessionname placeholder replaced

local f, err = io.open(ngx.config.prefix() .. "www/ipnbsess.tpl")
if f == nil then
    lognexit("ERROR: Unable to open IPNB template [", err, "]")
end

tpl = f:read("*a")
f:close()

out = string.gsub(tpl, "$$SESSNAME", sessname)
ngx.header['Set-Cookie'] = {'hostupl=' .. uplport ..'; path=/', 'hostipnb=' .. ipnbport .. '; path=/', 'sessname=' .. sessname .. '; path=/'}
ngx.say(out)

return