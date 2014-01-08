dofile(ngx.config.prefix() .. "lua/contutils.lua")

local upload = require "resty.upload"
local upload_dir = '/home/juser/'

local chunk_size = 8192
local form = upload:new(chunk_size)

local function my_get_file_name( res )
    if res[2] and string.find(res[2], 'filename') then
        local filename = string.match(res[2], 'filename="(.*)"')
        if filename then
            filename = trim(filename)
            if not(filename == "") then
                return filename
            else
                return
            end
        end
    end
end                

local file
while true do
    local typ, res, err = form:read()

    if not typ then
        ngx.log(ngx.ERR, "failed to read: ", err)
        response_errmsg = "<h3>ERROR : Error reading uploaded file</h3>"
        return writeout_uplpage()
    end

    if typ == "header" then
        local file_name = my_get_file_name(res)
        if file_name then
            file = io.open(upload_dir .. file_name, "w+")
            if not file then
                ngx.log(ngx.ERR, "failed to open file ", file_name)
                response_errmsg = "<h3>ERROR : Error writing file ".. file_name .. "</h3>"
                return writeout_uplpage()
            end
        end

    elseif typ == "body" then
        if file then
            file:write(res)
        end

    elseif typ == "part_end" then
        if file then
            file:close()
        end
        file = nil

    elseif typ == "eof" then
        break

    else
        -- do nothing
    end
end

writeout_uplpage()

