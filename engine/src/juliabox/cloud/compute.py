__author__ = 'tan'

import socket
import fcntl
import struct
from juliabox.jbox_util import LoggerMixin, JBoxPluginType, JBoxCfg
import random


class JBPluginCloud(LoggerMixin):
    """ Interfaces with cloud service providers or provides similar services locally.

    - `JBPluginCloud.JBP_BUCKETSTORE`, `JBPluginCloud.JBP_BUCKETSTORE_S3`:
        Provides storage for blobs of data in named buckets. Similar to Amazon S3 or OpenStack Swift.
        - `push(bucket, local_file, metadata=None)`
        - `pull(bucket, local_file, metadata_only=False)`
        - `delete(bucket, local_file)`
        - `copy(from_file, to_file, from_bucket, to_bucket=None)`
        - `move(from_file, to_file, from_bucket, to_bucket=None)`
    - `JBPluginCloud.JBP_DNS`, `JBPluginCloud.JBP_DNS_ROUTE53`:
        DNS service.
        - `configure()`: Read and store configuration from JBoxCfg.
        - `domain()`: Return the domain name configured to be used
        - `add_cname(name, value)`: Add a CNAME entry
        - `delete_cname(name)`: Delete the specified CNAME entry.
    - `JBPluginCloud.JBP_SENDMAIL`, `JBPluginCloud.JBP_SENDMAIL_SES`:
        E-Mail sending service.
        - `configure()`: Read and store configuration from JBoxCfg.
        - `get_email_rates()`: Rate limits to adhere to, as `daily_quota_remaining`,`rate_per_sec`
        - `send_email(rcpt, sender, subject, body)`: Send email as specified.
    - `JBPluginCloud.JBP_COMPUTE`, `JBPluginCloud.JBP_COMPUTE_EC2`, `JBPluginCloud.JBP_COMPUTE_SINGLENODE`:
        Compute facility - start/stop instances to scale the cluster up or down based on the decided loading pattern,
        DNS, record and query load statistics which will be used in scaling decisions.
        - `configure()`: Read and store configuration from JBoxCfg.
        - `get_install_id()`: Returns an unique ID for the installation. This allows multiple installations on shared infrastructure.
        - `get_instance_id()`: Returns an identifier for each instance/machine.
        - `get_alias_hostname()`: Returns a hostname belonging to the installation domain with which the current instance can be reached.
        - `get_all_instances(gname=None)`
        - `get_instance_public_hostname(instance_id=None)`: hostname accessing from public network (may not be same as get_alias_hostname)
        - `get_instance_local_hostname(instance_id=None)`: hostname accessible within the cluster, but not from public network
        - `get_instance_public_ip(instance_id=None)`
        - `get_instance_local_ip(instance_id=None)`
        - `publish_stats(stat_name, stat_unit, stat_value)`: Record performance/load statistics.
        - `publish_stats_multi(stats)`: Record multiple performance/load statistics.
        - `get_instance_stats(instance, stat_name, namespace=None)`: Query recorded statistics.
        - `get_cluster_stats(stat_name, namespace=None)`: Query cluster wide recorded statistics.
        - `get_cluster_average_stats(stat_name, namespace=None, results=None)`: Query cluster wide averages of recorded statistics.
        - `terminate_instance(instance=None)`: Terminate the specified instance. Self if instance is None.
        - `can_terminate(is_leader)`: Whether the instance can be terminated now (to scale down).
        - `should_accept_session(is_leader)`: Whether the instance can accept more load.
        - `get_redirect_instance_id()`: If the current instance is not ready to accept further load, a suggestion on which instance to load instead.
        - `get_image_recentness(instance=None)`: Whether the application image running on the instance is the latest.
        - `get_available_instances()`: Returns a list of instance props when using fixed size cluster.
    """

    JBP_BUCKETSTORE = "cloud.bucketstore"
    JBP_BUCKETSTORE_S3 = "cloud.bucketstore.s3"
    JBP_BUCKETSTORE_GS = "cloud.bucketstore.gs"

    JBP_DNS = "cloud.dns"
    JBP_DNS_ROUTE53 = "cloud.dns.route53"
    JBP_DNS_GCD = "cloud.dns.gcd"

    JBP_SENDMAIL = "cloud.sendmail"
    JBP_SENDMAIL_SES = "cloud.sendmail.ses"
    JBP_SENDMAIL_SMTP = "cloud.sendmail.smtp"

    JBP_COMPUTE = "cloud.compute"
    JBP_COMPUTE_EC2 = "cloud.compute.ec2"
    JBP_COMPUTE_SINGLENODE = "cloud.compute.singlenode"
    JBP_COMPUTE_GCE = "cloud.compute.gce"

    JBP_MIGRATE = "cloud.migrate"

    JBP_MONITORING = "cloud.monitoring"
    JBP_MONITORING_GOOGLE = "cloud.monitoring.google"
    JBP_MONITORING_GOOGLE_V2 = "cloud.monitoring.google.v2"
    JBP_MONITORING_GOOGLE_V3 = "cloud.monitoring.google.v3"

    JBP_SCALER = "cloud.scaler"

    __metaclass__ = JBoxPluginType


class Compute(LoggerMixin):
    impl = None
    SCALE = False

    @staticmethod
    def configure():
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_COMPUTE)
        if plugin is None:
            Compute.log_error("No plugin found for compute host")
            raise Exception("No plugin found for compute host")

        plugin.configure()
        Compute.impl = plugin
        Compute.SCALE = JBoxCfg.get('cloud_host.scale_down')

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
    def get_instance_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        siocgifaddr = 0x8915
        ifn = struct.pack('256s', ifname[:15])
        addr = fcntl.ioctl(s.fileno(), siocgifaddr, ifn)[20:24]
        return socket.inet_ntoa(addr)

    @staticmethod
    def get_docker_bridge_ip():
        return Compute.get_instance_interface_ip('docker0')

    @staticmethod
    def get_instance_local_ip(instance_id=None):
        return Compute.impl.get_instance_local_ip(instance_id)

    @staticmethod
    def publish_stats(stat_name, stat_unit, stat_value):
        return Compute.impl.publish_stats(stat_name, stat_unit, stat_value)

    @staticmethod
    def publish_stats_multi(stats):
        return Compute.impl.publish_stats_multi(stats)

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
        if not Compute.SCALE:
            Compute.log_debug("not terminating as cluster size is fixed")
            return False
        return Compute.impl.can_terminate(is_leader)

    @staticmethod
    def get_available_instances():
        return Compute.impl.get_available_instances()

    @staticmethod
    def get_redirect_instance_id():
        if not Compute.SCALE:
            Compute.log_debug("cluster size is fixed")
            available_nodes = Compute.get_available_instances()
            if len(available_nodes) > 0:
                return random.choice(available_nodes)
            else:
                return None
        return Compute.impl.get_redirect_instance_id()

    @staticmethod
    def should_accept_session(is_leader):
        self_instance_id = Compute.get_instance_id()
        self_load = Compute.get_instance_stats(self_instance_id, 'Load')
        if not Compute.SCALE:
            accept = self_load < 100
            Compute.log_debug("cluster size is fixed. accept: %r", accept)
            return accept
        return Compute.impl.should_accept_session(is_leader)

    @staticmethod
    def get_image_recentness(instance=None):
        if not Compute.SCALE:
            Compute.log_debug("ignoring image recentness as cluster size is fixed")
            return 0
        return Compute.impl.get_image_recentness(instance)

    @staticmethod
    def register_instance_dns():
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_DNS)
        if plugin is None:
            return
        plugin.add_cname(Compute.get_alias_hostname(), Compute.get_instance_public_hostname())

    @staticmethod
    def deregister_instance_dns():
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_DNS)
        if plugin is None:
            return
        plugin.delete_cname(Compute.get_alias_hostname())
