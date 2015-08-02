from juliabox.cloud import Compute
from handler_base import JBoxHandler


class CorsHandler(JBoxHandler):
    def get(self):
        args = self.get_argument('m', default=None)

        if args is not None:
            self.log_debug("setting cookies")
            self.unpack(args)
            self.set_status(status_code=204)
            self.finish()
        else:
            args = self.pack()
            url = "//" + Compute.get_alias_hostname() + "/jboxcors/?m=" + args
            self.log_debug("redirecting to " + url)
            self.redirect(url)
