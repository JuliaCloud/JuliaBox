from tornado.web import RequestHandler
from jbox_util import LoggerMixin, read_config

__all__ = ["JBoxHandler"]

class JBoxHandler(RequestHandler, LoggerMixin):
    _config = read_config()
    def rendertpl(self, tpl, **kwargs):
        self.render("../www/" + tpl, **kwargs)

    def config(self, key=None, default=None):
        if key is None:
            return self._config
        if self._config.has_key(key):
            return self._config[key]
        else: return default
