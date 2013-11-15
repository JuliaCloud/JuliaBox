Name
====

lua-resty-http -simple- Simple Lua HTTP client driver for ngx_lua

Example
=======

    server {
      location /test {
        content_by_lua '
          local http   = require "resty.http.simple"

          local res, err = http.request("checkip.amazonaws.com", 80, {
          headers = { Cookie = "foo=bar"} })
          if not res then
            ngx.say("http failure: ", err)
            return
          end

          if res.status >= 200 and res.status < 300 then
            ngx.say("My IP is: " .. res.body)
          else
            ngx.say("Query returned a non-200 response: " .. res.status)
          end
        ';
      }
    }

API
===

request
---
`syntax: local res, err = http:new(host, port, options)`

Perform an http request.

Before actually resolving the host name and connecting to the remote
backend, this method will always look up the connection pool for
matched idle connections created by previous calls of this
method. This allows the module to handle HTTP keep alives.

An optional Lua `options` table can be specified to declare various options:

* `method`
: Specifies the request method, defaults to `GET`.
* `path`
: Specifies the path, defaults to `'/'`.
* `query`
: Specifies query parameters. Accepts either a string or a Lua table.
* `headers`
: Specifies request headers. Accepts a Lua table. 
* `timeout`
: Sets the timeout in milliseconds for network operations. Defaults to `5000`.
* `version`
: Sets the HTTP version. Use `0` for HTTP/1.0 and `1` for
HTTP/1.1. Defaults to `1`.
* `maxsize`
: Sets the maximum size in bytes to fetch. A response body larger than
this will cause the fucntion to return a `exceeds maxsize`
error. Defaults to `nil` which means no limit.


Returns a `res` object containing three attributes:

* `res.status` (number)
: The resonse status, e.g. 200
* `res.headers` (table)
: A Lua table with response headers. 
* `res.body` (string)
: The plain response body

**Note** All headers (request and response) are noramlized for
capitalization - e.g., Accept-Encoding, ETag, Foo-Bar, Baz - in the
normal HTTP "standard."

Licence
=======

Started life as a fork of
[lua-resty-http](https://github.com/bsm/lua-resty-http) - Copyright (c) 2013 Black Square Media Ltd

This code is covered by MIT License. 

Copyright (C) 2013, by Brian Akins <brian@akins.org>.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
