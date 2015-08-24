__author__ = 'tan'

import datetime
import sys
import pytz
import boto
import boto.utils
import boto.ec2
import boto.ec2.cloudwatch
import boto.ec2.autoscale

from juliabox.cloud import JBPluginCloud
from juliabox.jbox_util import JBoxCfg, parse_iso_time, retry


class CompEC2(JBPluginCloud):
    provides = [JBPluginCloud.JBP_COMPUTE, JBPluginCloud.JBP_COMPUTE_EC2]

    REGION = 'us-east-1'
    ZONE = None
    INSTALL_ID = 'JuliaBox'

    EC2_CONN = None
    CLOUDWATCH_CONN = None
    AUTOSCALE_CONN = None

    AUTOSCALE_GROUP = None
    SCALE_UP_POLICY = None
    SCALE_UP_AT_LOAD = 80

    INSTANCE_ID = None
    INSTANCE_IMAGE_VERS = {}

    PUBLIC_HOSTNAME = None
    LOCAL_HOSTNAME = None
    LOCAL_IP = None
    PUBLIC_IP = None

    SELF_STATS = dict()

    @staticmethod
    def configure():
        CompEC2.SCALE_UP_AT_LOAD = JBoxCfg.get('cloud_host.scale_up_at_load', 80)
        CompEC2.SCALE_UP_POLICY = JBoxCfg.get('cloud_host.scale_up_policy', None)
        CompEC2.AUTOSCALE_GROUP = JBoxCfg.get('cloud_host.autoscale_group', None)

        CompEC2.INSTALL_ID = JBoxCfg.get('cloud_host.install_id', 'JuliaBox')
        CompEC2.REGION = JBoxCfg.get('cloud_host.region', 'us-east-1')

    @staticmethod
    def get_install_id():
        return CompEC2.INSTALL_ID

    @staticmethod
    def get_instance_id():
        if CompEC2.INSTANCE_ID is None:
            CompEC2.INSTANCE_ID = boto.utils.get_instance_metadata()['instance-id']
        return CompEC2.INSTANCE_ID

    @staticmethod
    def _make_alias_hostname(instance_id=None):
        dns_name = CompEC2.get_instance_id() if instance_id is None else instance_id
        if CompEC2.AUTOSCALE_GROUP is not None:
            dns_name += ('-' + CompEC2.AUTOSCALE_GROUP)
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_DNS)
        dns_name += ('.' + plugin.domain())

        return dns_name

    @staticmethod
    def get_alias_hostname():
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_DNS)
        if plugin is None:
            return CompEC2.get_instance_public_hostname()
        return CompEC2._make_alias_hostname()

    @staticmethod
    def get_instance_public_hostname(instance_id=None):
        if instance_id is None:
            if CompEC2.PUBLIC_HOSTNAME is None:
                CompEC2.PUBLIC_HOSTNAME = boto.utils.get_instance_metadata()['public-hostname']
            return CompEC2.PUBLIC_HOSTNAME
        else:
            attrs = CompEC2._instance_attrs(instance_id)
            return attrs.dns_name

    @staticmethod
    def get_instance_local_hostname(instance_id=None):
        if instance_id is None:
            if CompEC2.LOCAL_HOSTNAME is None:
                CompEC2.LOCAL_HOSTNAME = boto.utils.get_instance_metadata()['local-hostname']
            return CompEC2.LOCAL_HOSTNAME
        else:
            attrs = CompEC2._instance_attrs(instance_id)
            return attrs.private_dns_name

    @staticmethod
    def get_instance_public_ip(instance_id=None):
        if instance_id is None:
            if CompEC2.PUBLIC_IP is None:
                CompEC2.PUBLIC_IP = boto.utils.get_instance_metadata()['public-ipv4']
            return CompEC2.PUBLIC_IP
        else:
            attrs = CompEC2._instance_attrs(instance_id)
            return attrs.ip_address

    @staticmethod
    def get_instance_local_ip(instance_id=None):
        if instance_id is None:
            if CompEC2.LOCAL_IP is None:
                CompEC2.LOCAL_IP = boto.utils.get_instance_metadata()['local-ipv4']
            return CompEC2.LOCAL_IP
        else:
            attrs = CompEC2._instance_attrs(instance_id)
            return attrs.private_ip_address

    @staticmethod
    def publish_stats(stat_name, stat_unit, stat_value):
        """ Publish custom cloudwatch statistics. Used for status monitoring and auto scaling. """
        CompEC2.SELF_STATS[stat_name] = stat_value
        dims = {'InstanceID': CompEC2.get_instance_id()}
        CompEC2.log_info("CloudWatch %s.%s.%s=%r(%s)", CompEC2.INSTALL_ID, CompEC2.get_instance_id(),
                         stat_name, stat_value, stat_unit)
        CompEC2._connect_cloudwatch().put_metric_data(namespace=CompEC2.INSTALL_ID, name=stat_name,
                                                      unit=stat_unit, value=stat_value, dimensions=dims)

    @staticmethod
    def get_instance_stats(instance, stat_name, namespace=None):
        if (instance == CompEC2.get_instance_id()) and (stat_name in CompEC2.SELF_STATS):
            CompEC2.log_debug("Using cached self_stats. %s=%r", stat_name, CompEC2.SELF_STATS[stat_name])
            return CompEC2.SELF_STATS[stat_name]

        if namespace is None:
            namespace = CompEC2.INSTALL_ID
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(minutes=30)
        res = None
        results = CompEC2._connect_cloudwatch().get_metric_statistics(60, start, end, stat_name, namespace,
                                                                      'Average', {'InstanceID': [instance]})
        for _res in results:
            if (res is None) or (res['Timestamp'] < _res['Timestamp']):
                res = _res
        return res['Average'] if res else None

    @staticmethod
    def _get_metric_dimensions(metric_name, metric_namespace=None):
        if metric_namespace is None:
            metric_namespace = CompEC2.INSTALL_ID

        next_token = None
        dims = {}

        while True:
            metrics = CompEC2._connect_cloudwatch().list_metrics(next_token=next_token,
                                                                 metric_name=metric_name,
                                                                 namespace=metric_namespace)
            for m in metrics:
                for n_dim, v_dim in m.dimensions.iteritems():
                    dims[n_dim] = dims.get(n_dim, []) + v_dim
            next_token = metrics.next_token
            if (next_token is None) or (len(next_token) == 0):
                break
        if len(dims) == 0:
            CompEC2.log_warn("invalid metric " + '.'.join([metric_namespace, metric_name]))
            return None
        return dims

    @staticmethod
    def get_cluster_stats(stat_name, namespace=None):
        dims = CompEC2._get_metric_dimensions(stat_name, namespace)
        if dims is None:
            return None

        instances = CompEC2.get_all_instances()

        stats = {}
        if 'InstanceID' in dims:
            for instance in dims['InstanceID']:
                if (instances is None) or (instance in instances):
                    instance_load = CompEC2.get_instance_stats(instance, stat_name, namespace)
                    if instance_load is not None:
                        stats[instance] = instance_load

        return stats

    @staticmethod
    def get_cluster_average_stats(stat_name, namespace=None, results=None):
        if results is None:
            results = CompEC2.get_cluster_stats(stat_name, namespace)

        vals = results.values()
        if len(vals) > 0:
            return float(sum(vals)) / len(vals)
        return None

    @staticmethod
    def terminate_instance(instance=None):
        if instance is None:
            instance = CompEC2.get_instance_id()

        CompEC2.log_info("Terminating instance: %s", instance)
        try:
            CompEC2._connect_autoscale().terminate_instance(instance, decrement_capacity=True)
        except:
            CompEC2.log_exception("Error terminating instance to scale down")

    @staticmethod
    def can_terminate(is_leader):
        uptime = CompEC2._uptime_minutes()

        # if uptime less than hour and half return false
        if uptime < 90:
            CompEC2.log_debug("not terminating as uptime (%r) < 90", uptime)
            return False

        # cluster leader stays
        if is_leader:
            CompEC2.log_debug("not terminating as this is the cluster leader")
            return False

        # older amis terminate while newer amis never terminate
        ami_recentness = CompEC2.get_image_recentness()
        CompEC2.log_debug("AMI recentness = %d", ami_recentness)
        if ami_recentness < 0:
            CompEC2.log_debug("Terminating because running an older AMI")
            return True
        elif ami_recentness > 0:
            CompEC2.log_debug("Not terminating because running a more recent AMI")
            return False

        # keep at least 1 machine running
        instances = CompEC2.get_all_instances()
        if len(instances) == 1:
            CompEC2.log_debug("not terminating as this is the only machine")
            return False

        return True

    @staticmethod
    def get_redirect_instance_id():
        cluster_load = CompEC2.get_cluster_stats('Load')
        cluster_load = {k: v for k, v in cluster_load.iteritems() if CompEC2.get_image_recentness(k) >= 0}
        avg_load = CompEC2.get_cluster_average_stats('Load', results=cluster_load)

        if avg_load >= 50:
            # exclude machines with load >= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v < avg_load]
        else:
            # exclude machines with load <= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v > avg_load]

        if len(filtered_nodes) == 0:
            filtered_nodes = cluster_load.keys()

        filtered_nodes.sort()
        CompEC2.log_info("Redirect to instance_id: %r", filtered_nodes[0])
        return filtered_nodes[0]

    @staticmethod
    def should_accept_session(is_leader):
        self_load = CompEC2.get_instance_stats(CompEC2.get_instance_id(), 'Load')
        CompEC2.log_debug("Self load: %r", self_load)

        cluster_load = CompEC2.get_cluster_stats('Load')
        CompEC2.log_debug("Cluster load: %r", cluster_load)

        # remove machines with older AMIs
        cluster_load = {k: v for k, v in cluster_load.iteritems() if CompEC2.get_image_recentness(k) >= 0}
        CompEC2.log_debug("Cluster load (excluding old amis): %r", cluster_load)

        avg_load = CompEC2.get_cluster_average_stats('Load', results=cluster_load)
        CompEC2.log_debug("Average load (excluding old amis): %r", avg_load)

        if avg_load >= CompEC2.SCALE_UP_AT_LOAD:
            CompEC2.log_warn("Requesting scale up as cluster average load %r > %r", avg_load, CompEC2.SCALE_UP_AT_LOAD)
            CompEC2._add_instance()

        if self_load >= 100:
            CompEC2.log_debug("Not accepting: fully loaded")
            return False

        # handle ami switchover. newer AMIs always accept, older AMIs always reject
        ami_recentness = CompEC2.get_image_recentness()
        CompEC2.log_debug("AMI recentness = %d", ami_recentness)
        if ami_recentness > 0:
            CompEC2.log_debug("Accepting: more recent AMI")
            return True
        elif ami_recentness < 0:
            CompEC2.log_debug("Not accepting: older AMI")
            return False

        # if cluster leader, then accept as this will stick around
        if is_leader:
            CompEC2.log_debug("Accepting: cluster leader")
            return True

        # if only instance, accept
        if len(cluster_load) < 1:
            CompEC2.log_debug("Accepting: only instance (new AMI)")
            return True

        if avg_load >= 50:
            if self_load >= avg_load:
                CompEC2.log_debug("Accepting: not least loaded (self load >= avg)")
                return True

            # exclude machines with load >= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v < avg_load]
        else:
            filtered_nodes = cluster_load.keys()

        # at low load values, sorting by load will be inaccurate, sort alphabetically instead
        filtered_nodes.sort()
        if filtered_nodes[0] == CompEC2.get_instance_id():
            CompEC2.log_debug("Accepting: top among sorted instances (%r)", filtered_nodes)
            return True

        CompEC2.log_debug("Not accepting: not at top among sorted instances (%r)", filtered_nodes)
        return False

    @staticmethod
    def _zone():
        if CompEC2.ZONE is None:
            CompEC2.ZONE = boto.utils.get_instance_metadata()['placement']['availability-zone']
        return CompEC2.ZONE

    @staticmethod
    def _image_version(inst_id):
        try:
            if inst_id not in CompEC2.INSTANCE_IMAGE_VERS:
                conn = CompEC2._connect_ec2()
                inst = conn.get_all_instances([inst_id])[0].instances[0]
                ami_id = inst.image_id
                ami = conn.get_image(ami_id)
                ami_name = ami.name
                ver = int(ami_name.split()[-1])
                CompEC2.INSTANCE_IMAGE_VERS[inst_id] = ver

            return CompEC2.INSTANCE_IMAGE_VERS[inst_id]
        except:
            CompEC2.log_exception("Exception finding image_version of %s", inst_id)
            return 0

    @staticmethod
    def _connect_ec2():
        if CompEC2.EC2_CONN is None:
            CompEC2.EC2_CONN = boto.ec2.connect_to_region(CompEC2.REGION)
        return CompEC2.EC2_CONN

    @staticmethod
    def _connect_cloudwatch():
        if CompEC2.CLOUDWATCH_CONN is None:
            CompEC2.CLOUDWATCH_CONN = boto.ec2.cloudwatch.connect_to_region(CompEC2.REGION)
        return CompEC2.CLOUDWATCH_CONN

    @staticmethod
    def _connect_autoscale():
        if CompEC2.AUTOSCALE_CONN is None:
            CompEC2.AUTOSCALE_CONN = boto.ec2.autoscale.connect_to_region(CompEC2.REGION)
        return CompEC2.AUTOSCALE_CONN

    @staticmethod
    def _instance_attrs(instance_id=None):
        if instance_id is None:
            instance_id = CompEC2.get_instance_id()
        attrs = CompEC2._connect_ec2().get_only_instances([instance_id])
        if len(attrs) > 0:
            return attrs[0]
        return None

    @staticmethod
    def _uptime_minutes(instance_id=None):
        attrs = CompEC2._instance_attrs(instance_id)
        lt = parse_iso_time(attrs.launch_time)
        nt = datetime.datetime.now(pytz.utc)
        uptime = nt - lt
        minutes = int(uptime.total_seconds()/60)
        return minutes

    @staticmethod
    def _get_autoscale_group(gname):
        conn = CompEC2._connect_autoscale()
        try:
            groups = conn.get_all_groups([gname])
            if len(groups) > 0:
                return groups[0]
        except Exception:
            CompEC2.log_error("Exception getting autoscale group %s", gname)

        return None

    @staticmethod
    def get_all_instances(gname=None):
        if gname is None:
            gname = CompEC2.AUTOSCALE_GROUP
        if gname is None:
            return [CompEC2.get_instance_id()]
        group = CompEC2._get_autoscale_group(gname)
        if (group is None) or (len(group.instances) == 0):
            return [CompEC2.get_instance_id()]
        instances_ids = [i.instance_id for i in group.instances]
        reservations = CompEC2._connect_ec2().get_all_reservations(instances_ids)
        instances = [i.id for r in reservations for i in r.instances]
        return instances

    @staticmethod
    def _add_instance():
        try:
            CompEC2._connect_autoscale().execute_policy(CompEC2.SCALE_UP_POLICY,
                                                        as_group=CompEC2.AUTOSCALE_GROUP,
                                                        honor_cooldown='true')
        except:
            CompEC2.log_exception("Error requesting scale up")

    @staticmethod
    def get_image_recentness(instance=None):
        instances = CompEC2.get_all_instances()
        if instances is None:
            return 0
        max_ami_ver = 0
        min_ami_ver = sys.maxint
        for inst in instances:
            ami_ver = CompEC2._image_version(inst)
            max_ami_ver = max(max_ami_ver, ami_ver)
            min_ami_ver = min(min_ami_ver, ami_ver)

        if instance is None:
            instance = CompEC2.get_instance_id()
        self_ami_ver = CompEC2._image_version(instance)
        CompEC2.log_debug("ami versions: max: %d, min: %d, self(%s):%d", max_ami_ver, min_ami_ver,
                          instance, self_ami_ver)
        if self_ami_ver == 0:
            return 0
        elif max_ami_ver > self_ami_ver:
            return -1
        elif min_ami_ver < self_ami_ver:
            return 1
        else:
            return 0

    @staticmethod
    def _state_check(obj, state):
        obj.update()
        classname = obj.__class__.__name__
        if classname in ('Snapshot', 'Volume'):
            return obj.status == state
        else:
            return obj.state == state

    @staticmethod
    @retry(10, 0.5, backoff=1.5)
    def _wait_for_status(resource, state):
        return CompEC2._state_check(resource, state)

    @staticmethod
    @retry(15, 0.5, backoff=1.5)
    def _wait_for_status_extended(resource, state):
        return CompEC2._state_check(resource, state)
