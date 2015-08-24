import random
import requests
from locust import HttpLocust, TaskSet

# disable warnings from printing
requests.packages.urllib3.disable_warnings()

# register APIs fib1 to fib10 with the following code:
# fib(n::AbstractString) = fib(parse(Int, n)); fib(n::Int) = (n < 2) ? n : (fib(n-1) + fib(n-2)); process([(fib, false)]);


def pyfib(n):
    if n == 1 or n == 2:
        return 1
    elif n == 0:
        return 0
    return pyfib(n-1) + pyfib(n-2)


def check_response(response, n):
    resp = response.content.strip()
    val = int(resp)
    expected = pyfib(n)
    if val != expected:
        response.failure("Expected fib(%d)=%d. Got %d" % (n, expected, val))
    else:
        response.success()


def genfib(apiname):
    def _fib(l):
        n = random.randint(0, 10)
        response = l.client.get("/%s/fib/%d" % (apiname, n), catch_response=True, verify=False)
        check_response(response, n)

    _fib.__name__ = apiname
    return _fib

fibs = [genfib("fib%d" % (idx,)) for idx in range(1, 11)]


class UserBehavior(TaskSet):
    tasks = {fibs[i]: i for i in range(0, 10)}


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 10000
