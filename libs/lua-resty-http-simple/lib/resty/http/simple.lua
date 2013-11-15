local pairs    = pairs
local type     = type
local tonumber = tonumber
local tostring = tostring
local setmetatable = setmetatable
local encode_args  = ngx.encode_args
local tcp    = ngx.socket.tcp
local concat = table.concat
local insert = table.insert
local upper  = string.upper
local lower  = string.lower
local sub    = string.sub
local sfind  = string.find
local gmatch = string.gmatch
local gsub = string.gsub
local ipairs = ipairs
local rawset = rawset
local rawget = rawget
local min = math.min
local ngx = ngx

module(...)

_VERSION = "0.1.0"

--------------------------------------
-- LOCAL CONSTANTS                  --
--------------------------------------
local HTTP_1_1   = " HTTP/1.1\r\n"
local HTTP_1_0   = " HTTP/1.0\r\n"

local USER_AGENT = "Resty/HTTP-Simple " .. _VERSION .. " (Lua)"

-- canonical names for common headers
local common_headers = {
    "Cache-Control",
    "Content-Length", 
    "Content-Type", 
    "Date",
    "ETag",
    "Expires",
    "Host",
    "Location",
    "User-Agent"
}

for _,key in ipairs(common_headers) do
    rawset(common_headers, key, key)
    rawset(common_headers, lower(key), key)
end

function normalize_header(key)
    local val = common_headers[key]
    if val then
	return val
    end
    key = lower(key)
    val = common_headers[lower(key)]
    if val then
	return val
    end
    -- normalize it ourselves. do not cache it as we could explode our memory usage
    key = gsub(key, "^%l", upper)
    key = gsub(key, "-%l", upper)
    return key
end


--------------------------------------
-- LOCAL HELPERS                    --
--------------------------------------

local function _req_header(self, opts)
    -- Initialize request
    local req = {
	upper(opts.method or "GET"),
	" "
    }

    -- Append path
    local path = opts.path
    if type(path) ~= "string" then
	path = "/"
    elseif sub(path, 1, 1) ~= "/" then
	path = "/" .. path
    end
    insert(req, path)

    -- Normalize query string
    if type(opts.query) == "table" then
	opts.query = encode_args(opts.query)
    end

    -- Append query string
    if type(opts.query) == "string" then
	insert(req, "?" .. opts.query)
    end

    -- Close first line
    if opts.version == 1 then
	insert(req, HTTP_1_1)
    else
	insert(req, HTTP_1_0)
    end

    -- Normalize headers
    opts.headers = opts.headers or {}
    local headers = {}
    for k,v in pairs(opts.headers) do
	headers[normalize_header(k)] = v
    end
    
    if opts.body then
	headers['Content-Length'] = #opts.body
    end
    if not headers['Host'] then
	headers['Host'] = self.host
    end
    if not headers['User-Agent'] then
	headers['User-Agent'] = USER_AGENT
    end
    if not headers['Accept'] then
	headers['Accept'] = "*/*"
    end
    if version == 0 and not headers['Connection'] then
	headers['Connection'] = "Keep-Alive"
    end
    
    -- Append headers
    for key, values in pairs(headers) do
	if type(values) ~= "table" then
	    values = {values}
	end
	
	key = tostring(key)
	for _, value in pairs(values) do
	    insert(req, key .. ": " .. tostring(value) .. "\r\n")
	end
    end
    
    -- Close headers
    insert(req, "\r\n")
    
    return concat(req)
end

local function _parse_headers(sock)
    local headers = {}
    local mode    = nil
    
    repeat
	local line = sock:receive()
	
	for key, val in gmatch(line, "([%w%-]+)%s*:%s*(.+)") do
	    key = normalize_header(key)
	    if headers[key] then
		local delimiter = ", "
		if key == "Set-Cookie" then
		    delimiter = "; "
		end
		headers[key] = headers[key] .. delimiter .. tostring(val)
	    else
		headers[key] = tostring(val)
	    end
	end
    until sfind(line, "^%s*$")
    
    return headers, nil
end

local function _receive_length(sock, length)
    local chunks = {}

    local chunk, err = sock:receive(length)
    if not chunk then
	return nil, err
    end
    
    return chunk, nil
end


local function _receive_chunked(sock, maxsize)
    local chunks = {}

    local size = 0
    local done = false
    repeat
	local str, err = sock:receive("*l")
	if not str then
	    return nil, err
	end

	local length = tonumber(str, 16)
	
	if not length then
	    return nil, "unable to read chunksize"
	end

	size = size + length
	if maxsize and size > maxsize then
	    return nil, 'exceeds maxsize'
	end
	
	if length > 0 then
	    local str, err = sock:receive(length)
	    if not str then
		return nil, err
	    end
	    insert(chunks, str)
	else
	    done = true
	end
	-- read the \r\n
	sock:receive(2)
    until done

    return concat(chunks), nil
end

local function _receive_all(sock, maxsize)
    -- we read maxsize +1 for the corner case where the upstream wants to write
    -- exactly maxsize bytes
    local arg = maxsize and (maxsize + 1) or "*a"
    local chunk, err, partial = sock:receive(arg)
    if maxsize then
	-- if we didn't get an error, it means that the upstream still had data to write
	-- which means it exceeded maxsize
	if not err then
	      return nil, 'exceeds maxsize'
	else
	    -- you read to closed in this situation so, if upstream did not close
	    -- then its an error
	    if err ~= "closed" then
		return nil, err
	    else
		-- this seems odd but is correct, bcs of how ngx_lua
		-- handled the rror case, which is actually a success
		-- in this scenerio
		chunk = partial
	    end
	end
    end

    -- in the case of reading all til closed, closed is not a "valid" error
    if not chunk then
	return nil, err
    end
    return chunk, nil
end

local function _receive(self, sock)
    local line, err = sock:receive()
    if not line then
	return nil, err
    end

    local status = tonumber(sub(line, 10, 12))

    local headers, err = _parse_headers(sock)
    if not headers then
	return nil, err
    end

    local maxsize = self.opts.maxsize
       
    local length = tonumber(headers["Content-Length"])
    local body
    local err
    
    local keepalive = true
       
    if length then
	if maxsize and length > maxsize then
	    body, err =  nil, 'exceeds maxsize'
	else
	    body, err = _receive_length(sock, length)
	end
    else
	local encoding = headers["Transfer-Encoding"]
	if encoding and lower(encoding) == "chunked" then
	    body, err = _receive_chunked(sock, maxsize)
	else
	    body, err = _receive_all(sock, maxsize)
	    keepalive = false
	end
    end
    
    if not body then 
	keepalive = false
    end
    
    if keepalive then
	local connection = headers["Connection"]
	conenction = connection and lower(connection) or nil
	if connection then
	    if connection == "close" then
		keepalive = false
	    end
	else
	    if self.version == 0 then
		keepalive = false
	    end
	end
    end
    
    if keepalive then
	sock:setkeepalive()
    else
	sock:close()
    end
    
    return { status = status, headers = headers, body = body }
end


--------------------------------------
-- PUBLIC API                       --
--------------------------------------

function request(host, port, opts)
    opts = opts or {}
    local sock, err = tcp()
    if not sock then
	return nil, err
    end

    sock:settimeout(opts.timeout or 5000)
    
    local rc, err = sock:connect(host, port)
    if not rc then
	return nil, err
    end
    
    local version = opts.version
    if version then
	if version ~= 0 and version ~= 1 then
	    return nil, "unknown HTTP version"
	end
    else
	opts.version = 1
    end
    
    local self = {
	host = host,
	port = port,
	sock = sock,
	opts = opts
    }

    -- Build and send request header
    local header = _req_header(self, opts)
    local bytes, err = sock:send(header)
    if not bytes then
	return nil, err
    end

    -- Send the body if there is one
    if opts and type(opts.body) == "string" then
	local bytes, err = sock:send(opts.body)
	if not bytes then
	    return nil, err
	end
    end

    return _receive(self, sock)
end

