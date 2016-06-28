from handler_base import JBoxHandler
from juliabox.jbox_util import JBoxCfg
from juliabox.jbox_crypto import signstr
from juliabox.cloud import Compute
from juliabox.db import JBoxInstanceProps

__author__ = 'tan'


class APIInfoHandler(JBoxHandler):
    def get(self):
        self.log_debug("APIInfo handler got GET request")
        key = self.get_argument("key", None)
        sign = self.get_argument("sign", None)

        if key is None or sign is None:
            self.send_error()
            return
        sign2 = signstr(key, JBoxCfg.get('sesskey'))

        if sign != sign2:
            self.log_info("signature mismatch. key:%r sign:%r expected:%r", key, sign, sign2)
            self.send_error()
            return

        api_status = JBoxInstanceProps.get_instance_status(Compute.get_install_id())
        self.log_info("cluster api status: %r", api_status)

        # filter out instances that should not accept more load
        filtered_api_status = {k: v for (k, v) in api_status.iteritems() if v['accept']}
        preferred_instances = filtered_api_status.keys()

        # flip the dict
        per_api_instances = dict()
        for (inst, status) in filtered_api_status.iteritems():
            api_names = status['api_status'].keys()
            for api_name in api_names:
                v = per_api_instances.get(api_name, [])
                v.append(inst)

        per_api_instances[" preferred "] = preferred_instances
        self.log_info("per api instances: %r", per_api_instances)
        self.write(per_api_instances)
        return
