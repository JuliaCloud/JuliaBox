use lib 'lib';
use Test::Nginx::Socket;
use Cwd qw(cwd);

repeat_each(2);

plan tests => repeat_each() * (3 * blocks());

my $pwd = cwd();

our $HttpConfig = qq{
    lua_package_path "$pwd/lib/?.lua;;";
};

$ENV{TEST_NGINX_RESOLVER} = '8.8.8.8';

no_long_string();

run_tests();

__DATA__

=== TEST 1: Header normalization
--- http_config eval: $::HttpConfig
--- config
    resolver $TEST_NGINX_RESOLVER;
    location /foo {
        content_by_lua '
	   ngx.header["foo-bar"] = "Foo-Bar"
	   ngx.header["foo-baz"] = "Foo-Baz"
	   ngx.header["etag"] = "ETag"
	   ngx.header["X-FOO-BAR"] = "X-Foo-Bar"
	   ngx.say("meh")
        ';
    }

    location /t {
        content_by_lua '
	    local http = require "resty.http.simple"
	    local res, err = http.request("127.0.0.1", 1984, { path = "/foo" })
	    headers = res.headers
	    ngx.say(headers["Foo-Bar"])
	    ngx.say(headers["Foo-Baz"])
	    ngx.say(headers["ETag"])
	    ngx.say(headers["X-Foo-Bar"])
        ';
    }
--- request
GET /t
--- response_body
Foo-Bar
Foo-Baz
ETag
X-Foo-Bar
--- no_error_log
[error]


