from tornado.web import RequestHandler

from jbox_util import LoggerMixin
from jbox_container import JBoxContainer
from jbox_crypto import signstr


class JBoxHandler(RequestHandler, LoggerMixin):
    _config = None

    def rendertpl(self, tpl, **kwargs):
        self.render("../../www/" + tpl, **kwargs)

    @classmethod
    def configure(cls, cfg):
        cls._config = cfg

    @classmethod
    def config(cls, key=None, default=None):
        if key is None:
            return cls._config
        if key in cls._config:
            return cls._config[key]
        else:
            return default

    @classmethod
    def is_valid_req(cls, req):
        sessname = req.get_cookie("sessname")
        if None == sessname:
            return False
        sessname = sessname.replace('"', '')
        hostshell = req.get_cookie("hostshell").replace('"', '')
        hostupl = req.get_cookie("hostupload").replace('"', '')
        hostipnb = req.get_cookie("hostipnb").replace('"', '')
        signval = req.get_cookie("sign").replace('"', '')

        sign = signstr(sessname + hostshell + hostupl + hostipnb, cls._config["sesskey"])
        if sign != signval:
            cls.log_info('not valid req. signature not matching')
            return False
        if not JBoxContainer.is_valid_container("/" + sessname, (hostshell, hostupl, hostipnb)):
            cls.log_info('not valid req. container deleted or ports not matching')
            return False
        return True
