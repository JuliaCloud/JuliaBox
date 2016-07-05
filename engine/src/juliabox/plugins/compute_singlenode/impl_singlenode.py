__author__ = 'tan'

import socket

from juliabox.cloud import JBPluginCloud
from juliabox.jbox_util import JBoxCfg
from juliabox.db import JBoxInstanceProps


class CompSingleNode(JBPluginCloud):
    provides = [JBPluginCloud.JBP_COMPUTE, JBPluginCloud.JBP_COMPUTE_SINGLENODE]

    INSTALL_ID = 'JuliaBox'

    PUBLIC_HOSTNAME = None
    LOCAL_HOSTNAME = None
    LOCAL_IP = None
    PUBLIC_IP = None

    SELF_STATS = dict()

    @staticmethod
    def configure():
        CompSingleNode.INSTALL_ID = JBoxCfg.get('cloud_host.install_id', 'JuliaBox')

    @staticmethod
    def get_install_id():
        return CompSingleNode.INSTALL_ID

    @staticmethod
    def get_instance_id():
        return 'localhost'

    @staticmethod
    def get_all_instances(gname=None):
        if gname is not None:
            CompSingleNode.log_warn("Unknown compute group: %s", gname)
        return [CompSingleNode.get_instance_id()]

    @staticmethod
    def _chk_instance_id(instance_id):
        if instance_id is not None and instance_id != CompSingleNode.get_instance_id():
            CompSingleNode.log_warn("Unknown instance id: %s", instance_id)

    @staticmethod
    def get_alias_hostname():
        return CompSingleNode.get_instance_public_hostname()

    @staticmethod
    def get_instance_public_hostname(instance_id=None):
        if CompSingleNode.PUBLIC_HOSTNAME is None:
            CompSingleNode._chk_instance_id(instance_id)
            CompSingleNode.PUBLIC_HOSTNAME = socket.getfqdn()
        return CompSingleNode.PUBLIC_HOSTNAME

    @staticmethod
    def get_instance_local_hostname(instance_id=None):
        if CompSingleNode.LOCAL_HOSTNAME is None:
            CompSingleNode._chk_instance_id(instance_id)
            CompSingleNode.LOCAL_HOSTNAME = socket.getfqdn()
        return CompSingleNode.LOCAL_HOSTNAME

    @staticmethod
    def get_instance_public_ip(instance_id=None):
        if CompSingleNode.PUBLIC_IP is None:
            CompSingleNode._chk_instance_id(instance_id)
            CompSingleNode.PUBLIC_IP = socket.gethostbyname(CompSingleNode.get_instance_public_hostname(instance_id))
        return CompSingleNode.PUBLIC_IP

    @staticmethod
    def get_instance_local_ip(instance_id=None):
        if CompSingleNode.LOCAL_IP is None:
            CompSingleNode._chk_instance_id(instance_id)
            CompSingleNode.LOCAL_IP = socket.gethostbyname(CompSingleNode.get_instance_local_hostname(instance_id))
        return CompSingleNode.LOCAL_IP

    @staticmethod
    def publish_stats(stat_name, stat_unit, stat_value):
        CompSingleNode.SELF_STATS[stat_name] = stat_value
        CompSingleNode.log_info("Stats: %s.%s.%s=%r(%s)",
                                CompSingleNode.INSTALL_ID, CompSingleNode.get_instance_id(),
                                stat_name, stat_value, stat_unit)

    @staticmethod
    def publish_stats_multi(stats):
        for (stat_name, stat_unit, stat_value) in stats:
            CompSingleNode.publish_stats(stat_name, stat_unit, stat_value)

    @staticmethod
    def get_instance_stats(instance, stat_name, namespace=None):
        stat_val = None
        if (instance == CompSingleNode.get_instance_id()) and (stat_name in CompSingleNode.SELF_STATS):
            stat_val = CompSingleNode.SELF_STATS[stat_name]
            CompSingleNode.log_debug("Using cached self_stats. %s=%r", stat_name, stat_val)
        return stat_val

    @staticmethod
    def get_cluster_stats(stat_name, namespace=None):
        if stat_name in CompSingleNode.SELF_STATS:
            return {CompSingleNode.get_instance_id(): CompSingleNode.SELF_STATS[stat_name]}
        else:
            return None

    @staticmethod
    def get_cluster_average_stats(stat_name, namespace=None, results=None):
        if results is None:
            results = CompSingleNode.get_cluster_stats(stat_name, namespace)

        vals = results.values()
        if len(vals) > 0:
            return float(sum(vals)) / len(vals)
        return None

    @staticmethod
    def terminate_instance(instance=None):
        CompSingleNode.log_warn("Can not terminate a single node instance")

    @staticmethod
    def can_terminate(is_leader):
        return False

    @staticmethod
    def get_redirect_instance_id():
        return None

    @staticmethod
    def should_accept_session(is_leader):
        self_load = CompSingleNode.get_instance_stats(CompSingleNode.get_instance_id(), 'Load')
        CompSingleNode.log_debug("Self load: %r", self_load)

        if self_load >= 100:
            CompSingleNode.log_debug("Not accepting: fully loaded")
            return False
        return True

    @staticmethod
    def get_image_recentness(instance=None):
        return 0

    @staticmethod
    def get_available_instances():
        JBoxInstanceProps.get_available_instances(CompSingleNode.get_install_id())
