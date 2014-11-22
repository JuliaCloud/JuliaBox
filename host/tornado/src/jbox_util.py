import os
import sys
import time
import errno
import hashlib
import math
import zmq
import logging

import isodate


def parse_iso_time(tm):
    if tm is not None:
        tm = isodate.parse_datetime(tm)
    return tm


def retry(tries, delay=1, backoff=2):
    """Retries a function or method until it returns True.

    delay sets the initial delay in seconds, and backoff sets the factor by which
    the delay should lengthen after each failure. backoff must be greater than 1,
    or else it isn't really a backoff. tries must be at least 0, and delay
    greater than 0.

    https://wiki.python.org/moin/PythonDecoratorLibrary#Retry"""

    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")

    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable

            rv = f(*args, **kwargs)  # first attempt
            while mtries > 0:
                if rv is True:  # Done on success
                    return True

                mtries -= 1      # consume an attempt
                time.sleep(mdelay)  # wait...
                mdelay *= backoff  # make future wait longer

                rv = f(*args, **kwargs)  # Try again

            return False  # Ran out of tries :-(

        return f_retry  # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator


# def log_info(s):
#     ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
#     print (ts + "  " + s)
#     sys.stdout.flush()


def esc_sessname(s):
    if s is None:
        return s
    return s.replace("@", "_at_").replace(".", "_")


def get_user_name(email):
    return email.split('@')[0]


def unique_sessname(s):
    if s is None:
        return None
    name = esc_sessname(s.split('@')[0])
    hashdigest = hashlib.sha1(s).hexdigest()
    return '_'.join([name, hashdigest])


def read_config():
    with open("conf/tornado.conf") as f:
        cfg = eval(f.read())

    def update_config(base_cfg, add_cfg):
        for n, v in add_cfg.iteritems():
            if (n in base_cfg) and isinstance(base_cfg[n], dict):
                update_config(base_cfg[n], v)
            else:
                base_cfg[n] = v

    if os.path.isfile("conf/jbox.user"):
        with open("conf/jbox.user") as f:
            ucfg = eval(f.read())
        update_config(cfg, ucfg)

    cfg["admin_sessnames"] = []
    for ad in cfg["admin_users"]:
        cfg["admin_sessnames"].append(unique_sessname(ad))

    cfg["protected_docknames"] = []
    for ps in cfg["protected_sessions"]:
        cfg["protected_docknames"].append("/" + unique_sessname(ps))

    return cfg


def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def _apply_to_path_element(path, file_fn, dir_fn, link_fn):
    if os.path.islink(path):
        link_fn(path)
    elif os.path.isfile(path):
        file_fn(path)
    elif os.path.isdir(path):
        dir_fn(path)
    else:
        raise Exception("Unknown file type for " + path)


def apply_to_path_elements(path, file_fn, dir_fn, link_fn, include_itself, topdown):
    for root, dirs, files in os.walk(path, topdown=topdown):
        for f in files:
            _apply_to_path_element(os.path.join(root, f), file_fn, dir_fn, link_fn)
        for d in dirs:
            _apply_to_path_element(os.path.join(root, d), file_fn, dir_fn, link_fn)

    if include_itself:
        _apply_to_path_element(path, file_fn, dir_fn, link_fn)


def ensure_writable(path, include_iteslf=False):
    apply_to_path_elements(path, lambda p: os.chmod(p, 0555), lambda p: os.chmod(p, 0777), lambda p: None,
                           include_iteslf, True)


def ensure_delete(path, include_itself=False):
    ensure_writable(path, include_itself)
    apply_to_path_elements(path, lambda p: os.remove(p), lambda p: os.rmdir(p), lambda p: os.remove(p), include_itself,
                           False)


def unquote(s):
    if s is None:
        return s
    s = s.strip()
    if s[0] == '"':
        return s[1:-1]
    else:
        return s


class LoggerMixin(object):
    _logger = None
    DEFAULT_LEVEL = logging.INFO

    @staticmethod
    def setup_logger(name=None, level=logging.INFO):
        logger = logging.getLogger(name)
        logger.setLevel(level)

        ch = logging.StreamHandler()
        ch.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        ch.setFormatter(formatter)

        logger.addHandler(ch)
        return logger

    @classmethod
    def _get_logger(cls):
        if cls._logger is None:
            name = cls.__name__
            if (len(cls.__module__) > 0) and (cls.__module__ != '__main__'):
                name = cls.__module__ + '.' + cls.__name__
            cls._logger = LoggerMixin.setup_logger(name, LoggerMixin.DEFAULT_LEVEL)
        return cls._logger

    @classmethod
    def log_info(cls, msg, *args, **kwargs):
        cls._get_logger().info(msg, *args, **kwargs)

    @classmethod
    def log_error(cls, msg, *args, **kwargs):
        cls._get_logger().error(msg, *args, **kwargs)

    @classmethod
    def log_exception(cls, msg, *args, **kwargs):
        cls._get_logger().exception(msg, *args, **kwargs)

    @classmethod
    def log_debug(cls, msg, *args, **kwargs):
        cls._get_logger().debug(msg, *args, **kwargs)


class JBoxAsyncJob(LoggerMixin):
    MODE_PUB = zmq.PUSH
    MODE_SUB = zmq.PULL

    CMD_BACKUP_CLEANUP = 1
    CMD_LAUNCH_SESSION = 2

    def __init__(self, port, mode):
        self._mode = mode
        self._ctx = zmq.Context()
        self._sock = self._ctx.socket(mode)
        addr = 'tcp://127.0.0.1:%d' % port
        if mode == JBoxAsyncJob.MODE_PUB:
            self._sock.bind(addr)
        else:
            self._sock.connect(addr)

    def send(self, cmd, data):
        assert self._mode == JBoxAsyncJob.MODE_PUB
        msg = {
            'cmd': cmd,
            'data': data
        }
        self._sock.send_json(msg)

    def recv(self):
        msg = self._sock.recv_json()
        return msg['cmd'], msg['data']