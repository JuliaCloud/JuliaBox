__author__ = 'tan'

from juliabox.jbox_util import LoggerMixin, JBoxPluginType


class JBoxCloudPlugin(LoggerMixin):
    """ The base class for cloud service providers.

    It is a plugin mount point, looking for features:
    - cloud.bucketstore (e.g. s3, swift)
    - cloud.dns (e.g. route53)
    - cloud.sendmail (e.g. ses)
    """

    PLUGIN_BUCKETSTORE = "cloud.bucketstore"
    PLUGIN_BUCKETSTORE_S3 = "cloud.bucketstore.s3"

    PLUGIN_DNS = "cloud.dns"
    PLUGIN_DNS_ROUTE53 = "cloud.dns.route53"

    PLUGIN_SENDMAIL = "cloud.sendmail"
    PLUGIN_SENDMAIL_SES = "cloud.sendmail.ses"

    PLUGIN_COMPUTE = "cloud.compute"
    PLUGIN_COMPUTE_EC2 = "cloud.compute.ec2"
    PLUGIN_COMPUTE_SINGLENODE = "cloud.compute.singlenode"

    __metaclass__ = JBoxPluginType


class Compute(LoggerMixin):
    impl = None

    @staticmethod
    def configure():
        plugin = JBoxCloudPlugin.jbox_get_plugin(JBoxCloudPlugin.PLUGIN_COMPUTE)
        if plugin is None:
            Compute.log_error("No plugin found for compute host")
            raise Exception("No plugin found for compute host")

        plugin.configure()
        Compute.impl = plugin

    @staticmethod
    def get_install_id():
        return Compute.impl.get_install_id()

    @staticmethod
    def get_instance_id():
        return Compute.impl.get_instance_id()

    @staticmethod
    def get_all_instances(gname=None):
        return Compute.impl.get_all_instances(gname)

    @staticmethod
    def get_alias_hostname():
        return Compute.impl.get_alias_hostname()

    @staticmethod
    def get_instance_public_hostname(instance_id=None):
        return Compute.impl.get_instance_public_hostname(instance_id)

    @staticmethod
    def get_instance_local_hostname(instance_id=None):
        return Compute.impl.get_instance_local_hostname(instance_id)

    @staticmethod
    def get_instance_public_ip(instance_id=None):
        return Compute.impl.get_instance_public_ip(instance_id)

    @staticmethod
    def get_instance_local_ip(instance_id=None):
        return Compute.impl.get_instance_local_ip(instance_id)

    @staticmethod
    def publish_stats(stat_name, stat_unit, stat_value):
        return Compute.impl.publish_stats(stat_name, stat_unit, stat_value)

    @staticmethod
    def get_instance_stats(instance, stat_name, namespace=None):
        return Compute.impl.get_instance_stats(instance, stat_name, namespace)

    @staticmethod
    def get_cluster_stats(stat_name, namespace=None):
        return Compute.impl.get_cluster_stats(stat_name, namespace)

    @staticmethod
    def get_cluster_average_stats(stat_name, namespace=None, results=None):
        return Compute.impl.get_cluster_average_stats(stat_name, namespace, results)

    @staticmethod
    def terminate_instance(instance=None):
        return Compute.impl.terminate_instance(instance)

    @staticmethod
    def can_terminate(is_leader):
        return Compute.impl.can_terminate(is_leader)

    @staticmethod
    def get_redirect_instance_id():
        return Compute.impl.get_redirect_instance_id()

    @staticmethod
    def should_accept_session(is_leader):
        return Compute.impl.should_accept_session(is_leader)

    @staticmethod
    def get_image_recentness(instance=None):
        return Compute.impl.get_image_recentness(instance)

    @staticmethod
    def register_instance_dns():
        plugin = JBoxCloudPlugin.jbox_get_plugin(JBoxCloudPlugin.PLUGIN_DNS)
        if plugin is None:
            return
        plugin.add_cname(Compute.get_alias_hostname(), Compute.get_instance_public_hostname())

    @staticmethod
    def deregister_instance_dns():
        plugin = JBoxCloudPlugin.jbox_get_plugin(JBoxCloudPlugin.PLUGIN_DNS)
        if plugin is None:
            return
        plugin.delete_cname(Compute.get_alias_hostname())