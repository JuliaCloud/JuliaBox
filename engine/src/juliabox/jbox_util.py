import os
import sh
import sys
import time
import errno
import hashlib
import math
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
                # tend = time.time() + mdelay
                # while time.time() < tend:
                #     LoggerMixin.log_debug("sleeping...")
                #     time.sleep(tend - time.time())  # wait...
                mdelay *= backoff  # make future wait longer

                rv = f(*args, **kwargs)  # Try again

            return False  # Ran out of tries :-(

        return f_retry  # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator


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
    if s.startswith('"'):
        return s[1:-1]
    else:
        return s


def create_host_mnt_command(cmd):
    pfx = os.getenv('HOST_MNT_PFX')
    if pfx:
        cmd = pfx + " " + cmd
    hcmd = sh.sudo
    for comp in cmd.split():
        hcmd = hcmd.bake(comp)
    return hcmd


def create_container_mnt_command(container_pid, cmd):
    pfx = os.getenv('CONT_MNT_PFX')
    if pfx:
        pfx = pfx.replace('{{CPID}}', str(container_pid))
        cmd = pfx + " " + cmd
    hcmd = sh.sudo
    for comp in cmd.split():
        hcmd = hcmd.bake(comp)
    return hcmd


class JBoxCfg(object):
    nv = None
    dckr = None

    @staticmethod
    def update_config(base_cfg, add_cfg):
        for n, v in add_cfg.iteritems():
            if (n in base_cfg) and isinstance(base_cfg[n], dict):
                JBoxCfg.update_config(base_cfg[n], v)
            else:
                base_cfg[n] = v

    @staticmethod
    def expand(cfg):
        cfg["admin_sessnames"] = []
        for ad in cfg["admin_users"]:
            cfg["admin_sessnames"].append(unique_sessname(ad))

    @staticmethod
    def load_plugins():
        for name in JBoxCfg.get('plugins'):
            if len(name) > 0:
                __import__(name)

    @classmethod
    def read(cls, *args):
        if len(args) == 0:
            JBoxCfg.read("../conf/tornado.conf", "../conf/jbox.user")

        cfg = None

        for arg in args:
            with open(arg) as f:
                arg_cfg = eval(f.read())
            if cfg is None:
                cfg = arg_cfg
            else:
                JBoxCfg.update_config(cfg, arg_cfg)

        JBoxCfg.expand(cfg)
        cls.nv = cfg
        JBoxCfg.load_plugins()

    @classmethod
    def get(cls, dotted_name, default=None):
        v = cls.nv
        for n in dotted_name.split('.'):
            v = v.get(n)
            if v is None:
                break
        return default if v is None else v


class LoggerMixin(object):
    _logger = None
    DEFAULT_LEVEL = logging.INFO

    @staticmethod
    def configure():
        LoggerMixin.setup_logger(level=JBoxCfg.get('root_log_level'))
        LoggerMixin.DEFAULT_LEVEL = JBoxCfg.get('jbox_log_level')

    @staticmethod
    def setup_logger(name=None, level=logging.INFO):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

        # default channel (stdout)
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # add separate channel (stderr) only for errors
        err_ch = logging.StreamHandler(stream=sys.stderr)
        err_ch.setLevel(logging.WARNING)
        err_ch.setFormatter(formatter)
        logger.addHandler(err_ch)

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
    def log_warn(cls, msg, *args, **kwargs):
        cls._get_logger().warning(msg, *args, **kwargs)

    @classmethod
    def log_error(cls, msg, *args, **kwargs):
        cls._get_logger().error(msg, *args, **kwargs)

    @classmethod
    def log_exception(cls, msg, *args, **kwargs):
        cls._get_logger().exception(msg, *args, **kwargs)

    @classmethod
    def log_critical(cls, msg, *args, **kwargs):
        cls._get_logger().critical(msg, *args, **kwargs)

    @classmethod
    def log_debug(cls, msg, *args, **kwargs):
        cls._get_logger().debug(msg, *args, **kwargs)


class JBoxPluginType(type):
    def __init__(cls, name, bases, attrs):
        super(JBoxPluginType, cls).__init__(name, bases, attrs)
        if not hasattr(cls, 'plugins'):
            cls.plugins = []
        else:
            cls.plugins.append(cls)

    def jbox_get_plugins(cls, feature):
        matches = []
        for plugin in cls.plugins:
            if hasattr(plugin, 'provides'):
                if feature in plugin.provides:
                    matches.append(plugin)
        return matches

    def jbox_get_plugin(cls, feature):
        for plugin in cls.plugins:
            if hasattr(plugin, 'provides'):
                if feature in plugin.provides:
                    return plugin
        return None
