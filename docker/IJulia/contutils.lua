local response_errmsg = ""

function writeout_uplpage()
    local f, err = io.open(ngx.config.prefix() .. "www/ipnbupl.tpl")
    if f == nil then
        ngx.log(ngx.ERR, "ERROR: Unable to open ipnbupl.tpl template [", err, "]")
        ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
    end

    tpl = f:read("*a")
    f:close()

    out = string.gsub(tpl, "$$ERRMSG", response_errmsg)
    ngx.say(out)
    return ngx.exit(0)
end

function trim(s)
    return s:find'^%s*$' and '' or s:match'^%s*(.*%S)'
end

