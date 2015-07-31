import datetime
import os
import pytz
import sys
import traceback

import boto.ec2
import boto.ec2.cloudwatch
import boto.ec2.autoscale
import boto.route53
import boto.ses
from boto.s3.key import Key
import boto.utils
import psutil

from juliabox.jbox_util import LoggerMixin, JBoxCfg, parse_iso_time, retry


class CloudHost(LoggerMixin):
    REGION = 'us-east-1'
    ZONE = None
    INSTALL_ID = 'JuliaBox'

    EC2_CONN = None

    ROUTE53_CONN = None
    ROUTE53_DOMAIN = ''

    S3_CONN = None
    S3_BUCKETS = {}

    CLOUDWATCH_CONN = None

    AUTOSCALE_CONN = None
    AUTOSCALE_GROUP = None
    SCALE_UP_POLICY = None
    SCALE_UP_AT_LOAD = 80

    SES_CONN = None

    ENABLED = {}
    INSTANCE_ID = None
    INSTANCE_IMAGE_VERS = {}
    PUBLIC_HOSTNAME = None
    LOCAL_HOSTNAME = None
    LOCAL_IP = None
    PUBLIC_IP = None
    SELF_STATS = {}
    # STATS_CACHE = {} # TODO: cache stats

    @staticmethod
    def instance_id():
        if CloudHost.INSTANCE_ID is None:
            if not CloudHost.ENABLED['cloudwatch']:
                CloudHost.log_debug('using localhost as instance_id')
                CloudHost.INSTANCE_ID = 'localhost'
            else:
                CloudHost.log_debug('getting instance_id from metadata')
                CloudHost.INSTANCE_ID = boto.utils.get_instance_metadata()['instance-id']
        return CloudHost.INSTANCE_ID

    @staticmethod
    def image_version(inst_id):
        try:
            if inst_id not in CloudHost.INSTANCE_IMAGE_VERS:
                conn = CloudHost.connect_ec2()
                inst = conn.get_all_instances([inst_id])[0].instances[0]
                ami_id = inst.image_id
                ami = conn.get_image(ami_id)
                ami_name = ami.name
                ver = int(ami_name.split()[-1])
                CloudHost.INSTANCE_IMAGE_VERS[inst_id] = ver

            return CloudHost.INSTANCE_IMAGE_VERS[inst_id]
        except:
            CloudHost.log_exception("Exception finding image_version of %s", inst_id)
            return 0

    @staticmethod
    def zone():
        if CloudHost.ZONE is None:
            if not CloudHost.ENABLED['cloudwatch']:
                CloudHost.ZONE = 'localhost'
            else:
                CloudHost.ZONE = boto.utils.get_instance_metadata()['placement']['availability-zone']
        return CloudHost.ZONE

    @staticmethod
    def notebook_websocket_hostname():
        if CloudHost.ENABLED['route53']:
            return CloudHost.make_instance_dns_name()
        return CloudHost.instance_public_hostname()

    @staticmethod
    def instance_public_hostname(instance_id=None):
        if instance_id is None:
            if CloudHost.PUBLIC_HOSTNAME is None:
                if not CloudHost.ENABLED['cloudwatch']:
                    CloudHost.PUBLIC_HOSTNAME = 'localhost'
                else:
                    CloudHost.PUBLIC_HOSTNAME = boto.utils.get_instance_metadata()['public-hostname']
            return CloudHost.PUBLIC_HOSTNAME
        else:
            attrs = CloudHost.instance_attrs(instance_id)
            return attrs.dns_name

    @staticmethod
    def instance_local_hostname(instance_id=None):
        if instance_id is None:
            if CloudHost.LOCAL_HOSTNAME is None:
                if not CloudHost.ENABLED['cloudwatch']:
                    CloudHost.LOCAL_HOSTNAME = 'localhost'
                else:
                    CloudHost.LOCAL_HOSTNAME = boto.utils.get_instance_metadata()['local-hostname']
            return CloudHost.LOCAL_HOSTNAME
        else:
            attrs = CloudHost.instance_attrs(instance_id)
            return attrs.private_dns_name

    @staticmethod
    def instance_public_ip(instance_id=None):
        if instance_id is None:
            if CloudHost.PUBLIC_IP is None:
                if not CloudHost.ENABLED['cloudwatch']:
                    CloudHost.PUBLIC_IP = '127.0.0.1'
                else:
                    CloudHost.PUBLIC_IP = boto.utils.get_instance_metadata()['public-ipv4']
            return CloudHost.PUBLIC_IP
        else:
            attrs = CloudHost.instance_attrs(instance_id)
            return attrs.ip_address

    @staticmethod
    def instance_local_ip(instance_id=None):
        if instance_id is None:
            if CloudHost.LOCAL_IP is None:
                if not CloudHost.ENABLED['cloudwatch']:
                    CloudHost.LOCAL_IP = '127.0.0.1'
                else:
                    CloudHost.LOCAL_IP = boto.utils.get_instance_metadata()['local-ipv4']
            return CloudHost.LOCAL_IP
        else:
            attrs = CloudHost.instance_attrs(instance_id)
            return attrs.private_ip_address

    @staticmethod
    def instance_attrs(instance_id=None):
        if instance_id is None:
            instance_id = CloudHost.instance_id()
        if instance_id != 'localhost':
            attrs = CloudHost.connect_ec2().get_only_instances([instance_id])
            if len(attrs) > 0:
                return attrs[0]
        return None

    @staticmethod
    def uptime_minutes(instance_id=None):
        if CloudHost.ENABLED['cloudwatch']:
            attrs = CloudHost.instance_attrs(instance_id)
            lt = parse_iso_time(attrs.launch_time)
            nt = datetime.datetime.now(pytz.utc)
            uptime = nt - lt
        elif instance_id is not None:
            uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
        else:
            CloudHost.log_debug("cloudwatch disabled. can not get uptime")
            return 0
        minutes = int(uptime.total_seconds()/60)
        return minutes

    @staticmethod
    def configure():
        CloudHost.ENABLED['s3'] = JBoxCfg.get('cloud_host.s3', True)
        CloudHost.ENABLED['cloudwatch'] = JBoxCfg.get('cloud_host.cloudwatch', True)
        CloudHost.ENABLED['autoscale'] = JBoxCfg.get('cloud_host.autoscale', True)
        CloudHost.ENABLED['route53'] = JBoxCfg.get('cloud_host.route53', True)
        CloudHost.ENABLED['ses'] = JBoxCfg.get('cloud_host.ses', True)

        CloudHost.SCALE_UP_AT_LOAD = JBoxCfg.get('cloud_host.scale_up_at_load', 80)
        CloudHost.SCALE_UP_POLICY = JBoxCfg.get('cloud_host.scale_up_policy', None)
        CloudHost.AUTOSCALE_GROUP = JBoxCfg.get('cloud_host.autoscale_group', None)

        CloudHost.ROUTE53_DOMAIN = JBoxCfg.get('cloud_host.route53_domain', None)

        CloudHost.INSTALL_ID = JBoxCfg.get('cloud_host.install_id', 'JuliaBox')
        CloudHost.REGION = JBoxCfg.get('cloud_host.region', 'us-east-1')

    @staticmethod
    def connect_ec2():
        if (CloudHost.EC2_CONN is None) and CloudHost.ENABLED['cloudwatch']:
            CloudHost.EC2_CONN = boto.ec2.connect_to_region(CloudHost.REGION)
        return CloudHost.EC2_CONN

    @staticmethod
    def connect_route53():
        if (CloudHost.ROUTE53_CONN is None) and CloudHost.ENABLED['route53']:
            CloudHost.ROUTE53_CONN = boto.route53.connect_to_region(CloudHost.REGION)
        return CloudHost.ROUTE53_CONN

    @staticmethod
    def connect_ses():
        if (CloudHost.SES_CONN is None) and CloudHost.ENABLED['ses']:
            CloudHost.SES_CONN = boto.ses.connect_to_region(CloudHost.REGION)
        return CloudHost.SES_CONN

    @staticmethod
    def make_instance_dns_name(instance_id=None):
        dns_name = CloudHost.instance_id() if instance_id is None else instance_id
        if CloudHost.AUTOSCALE_GROUP is not None:
            dns_name += ('-' + CloudHost.AUTOSCALE_GROUP)
        dns_name += ('.' + CloudHost.ROUTE53_DOMAIN)

        return dns_name

    @staticmethod
    def register_instance_dns():
        if not CloudHost.ENABLED['route53']:
            return

        dns_name = CloudHost.make_instance_dns_name()

        zone = CloudHost.connect_route53().get_zone(CloudHost.ROUTE53_DOMAIN)
        zone.add_cname(dns_name, CloudHost.instance_public_hostname())

    @staticmethod
    def deregister_instance_dns():
        if not CloudHost.ENABLED['route53']:
            return

        dns_name = CloudHost.make_instance_dns_name()

        zone = CloudHost.connect_route53().get_zone(CloudHost.ROUTE53_DOMAIN)
        zone.delete_cname(dns_name)

    @staticmethod
    def connect_s3():
        if (CloudHost.S3_CONN is None) and CloudHost.ENABLED['s3']:
            CloudHost.S3_CONN = boto.connect_s3()
        return CloudHost.S3_CONN

    @staticmethod
    def connect_s3_bucket(bucket):
        if not CloudHost.ENABLED['s3']:
            return None

        if bucket not in CloudHost.S3_BUCKETS:
            CloudHost.S3_BUCKETS[bucket] = CloudHost.connect_s3().get_bucket(bucket)
        return CloudHost.S3_BUCKETS[bucket]

    @staticmethod
    def connect_cloudwatch():
        if (CloudHost.CLOUDWATCH_CONN is None) and CloudHost.ENABLED['cloudwatch']:
            CloudHost.CLOUDWATCH_CONN = boto.ec2.cloudwatch.connect_to_region(CloudHost.REGION)
        return CloudHost.CLOUDWATCH_CONN

    @staticmethod
    def connect_autoscale():
        if (CloudHost.AUTOSCALE_CONN is None) and CloudHost.ENABLED['autoscale']:
            CloudHost.AUTOSCALE_CONN = boto.ec2.autoscale.connect_to_region(CloudHost.REGION)
        return CloudHost.AUTOSCALE_CONN

    @staticmethod
    def get_metric_dimensions(metric_name, metric_namespace=None):
        if metric_namespace is None:
            metric_namespace = CloudHost.INSTALL_ID

        next_token = None
        dims = {}

        while True:
            metrics = CloudHost.connect_cloudwatch().list_metrics(next_token=next_token,
                                                                  metric_name=metric_name,
                                                                  namespace=metric_namespace)
            for m in metrics:
                for n_dim, v_dim in m.dimensions.iteritems():
                    dims[n_dim] = dims.get(n_dim, []) + v_dim
            next_token = metrics.next_token
            if (next_token is None) or (len(next_token) == 0):
                break
        if len(dims) == 0:
            CloudHost.log_warn("invalid metric " + '.'.join([metric_namespace, metric_name]))
            return None
        return dims

    @staticmethod
    def publish_stats(stat_name, stat_unit, stat_value):
        """ Publish custom cloudwatch statistics. Used for status monitoring and auto scaling. """
        CloudHost.SELF_STATS[stat_name] = stat_value
        if not CloudHost.ENABLED['cloudwatch']:
            return

        dims = {'InstanceID': CloudHost.instance_id()}
        CloudHost.log_info("CloudWatch " + CloudHost.INSTALL_ID + "." + CloudHost.instance_id() + "." + stat_name
                           + "=" + str(stat_value) + "(" + stat_unit + ")")
        CloudHost.connect_cloudwatch().put_metric_data(namespace=CloudHost.INSTALL_ID, name=stat_name,
                                                       unit=stat_unit, value=stat_value, dimensions=dims)

    @staticmethod
    def instance_accept_session_priority(instance_id, load):
        # uptime = CloudHelper.uptime_minutes(instance_id)
        # uptime_last_hour = uptime_mins % 60
        # TODO:
        # - ami changeover
        # - hourly window
        # - load
        #return str(1000 + int(load)) + '_' + instance_id
        return instance_id

    @staticmethod
    def add_instance():
        if not CloudHost.ENABLED['autoscale']:
            return
        try:
            CloudHost.connect_autoscale().execute_policy(CloudHost.SCALE_UP_POLICY,
                                                         as_group=CloudHost.AUTOSCALE_GROUP,
                                                         honor_cooldown='true')
        except:
            CloudHost.log_error("Error requesting scale up")
            traceback.print_exc()

    @staticmethod
    def terminate_instance(instance=None):
        if not CloudHost.ENABLED['cloudwatch']:
            return

        if instance is None:
            instance = CloudHost.instance_id()

        CloudHost.log_info("Terminating instance: " + instance)
        try:
            if CloudHost.ENABLED['autoscale']:
                CloudHost.connect_autoscale().terminate_instance(instance, decrement_capacity=True)
            else:
                CloudHost.connect_ec2().terminate_instances(instance_ids=[instance])
        except:
            CloudHost.log_error("Error terminating instance to scale down")
            traceback.print_exc()

    @staticmethod
    def can_terminate(is_leader):
        if not CloudHost.ENABLED['cloudwatch']:
            return False

        uptime = CloudHost.uptime_minutes()

        # if uptime less than hour and half return false
        if (uptime is not None) and (uptime < 90):
            CloudHost.log_debug("not terminating as uptime (" + repr(uptime) + ") < 90")
            return False

        if not CloudHost.ENABLED['cloudwatch']:
            return False

        # cluster leader stays
        if is_leader:
            CloudHost.log_debug("not terminating as this is the cluster leader")
            return False

        # older amis terminate while newer amis never terminate
        ami_recentness = CloudHost.get_ami_recentness()
        CloudHost.log_debug("AMI recentness = %d", ami_recentness)
        if ami_recentness < 0:
            CloudHost.log_debug("Terminating because running an older AMI")
            return True
        elif ami_recentness > 0:
            CloudHost.log_debug("Not terminating because running a more recent AMI")
            return False

        # keep at least 1 machine running
        instances = CloudHost.get_autoscaled_instances()
        if len(instances) == 1:
            CloudHost.log_debug("not terminating as this is the only machine")
            return False

        return True

    @staticmethod
    def get_public_hostnames_by_tag(tag, value):
        conn = CloudHost.connect_ec2()
        instances = conn.get_only_instances(filters={"tag:"+tag: value, "instance-state-name": "running"})
        return [i.public_dns_name for i in instances]
        
    @staticmethod
    def get_private_hostnames_by_tag(tag, value):
        conn = CloudHost.connect_ec2()
        instances = conn.get_only_instances(filters={"tag:"+tag: value, "instance-state-name": "running"})
        return [i.private_dns_name for i in instances]

    @staticmethod
    def get_public_hostnames_by_placement_group(gname):
        conn = CloudHost.connect_ec2()
        instances = conn.get_only_instances(filters={"placement-group-name": gname, "instance-state-name": "running"})
        return [i.public_dns_name for i in instances]

    @staticmethod
    def get_public_ips_by_placement_group(gname):
        conn = CloudHost.connect_ec2()
        instances = conn.get_only_instances(filters={"placement-group-name": gname, "instance-state-name": "running"})
        return [i.ip_address for i in instances]

    @staticmethod
    def get_private_hostnames_by_placement_group(gname):
        conn = CloudHost.connect_ec2()
        instances = conn.get_only_instances(filters={"placement-group-name": gname, "instance-state-name": "running"})
        return [i.private_dns_name for i in instances]

    @staticmethod
    def get_private_ips_by_placement_group(gname):
        conn = CloudHost.connect_ec2()
        instances = conn.get_only_instances(filters={"placement-group-name": gname, "instance-state-name": "running"})
        return [i.private_ip_address for i in instances]

    @staticmethod
    def get_image(image_name):
        conn = CloudHost.connect_ec2()
        images = conn.get_all_images(owners='self')
        for image in images:
            if image.name == image_name:
                return image
        return None

    @staticmethod
    def get_redirect_instance_id():
        if not CloudHost.ENABLED['cloudwatch']:
            return None
        cluster_load = CloudHost.get_cluster_stats('Load')
        cluster_load = {k: v for k, v in cluster_load.iteritems() if CloudHost.get_ami_recentness(k) >= 0}
        avg_load = CloudHost.get_cluster_average_stats('Load', results=cluster_load)

        if avg_load >= 50:
            # exclude machines with load >= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v < avg_load]
        else:
            # exclude machines with load <= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v > avg_load]

        if len(filtered_nodes) == 0:
            filtered_nodes = cluster_load.keys()

        filtered_nodes.sort()
        CloudHost.log_info("Redirect to instance_id: %r", filtered_nodes[0])
        return filtered_nodes[0]

    @staticmethod
    def should_accept_session(is_leader):
        self_load = CloudHost.get_instance_stats(CloudHost.instance_id(), 'Load')
        CloudHost.log_debug("Self load: " + repr(self_load))

        if CloudHost.ENABLED['cloudwatch']:
            cluster_load = CloudHost.get_cluster_stats('Load')
            CloudHost.log_debug("Cluster load: %r", cluster_load)

            # remove machines with older AMIs
            cluster_load = {k: v for k, v in cluster_load.iteritems() if CloudHost.get_ami_recentness(k) >= 0}
            CloudHost.log_debug("Cluster load (excluding old amis): %r", cluster_load)

            avg_load = CloudHost.get_cluster_average_stats('Load', results=cluster_load)
            CloudHost.log_debug("Average load (excluding old amis): %r", avg_load)

            if avg_load >= CloudHost.SCALE_UP_AT_LOAD:
                CloudHost.log_warn("Requesting scale up as cluster average load %r > %r",
                                   avg_load, CloudHost.SCALE_UP_AT_LOAD)
                CloudHost.add_instance()
        else:
            avg_load = self_load
            cluster_load = []

        if self_load >= 100:
            CloudHost.log_debug("Not accepting: fully loaded")
            return False

        if not CloudHost.ENABLED['cloudwatch']:
            CloudHost.log_debug("Accepting: not in a cluster")
            return True

        # handle ami switchover. newer AMIs always accept, older AMIs always reject
        ami_recentness = CloudHost.get_ami_recentness()
        CloudHost.log_debug("AMI recentness = %d", ami_recentness)
        if ami_recentness > 0:
            CloudHost.log_debug("Accepting: more recent AMI")
            return True
        elif ami_recentness < 0:
            CloudHost.log_debug("Not accepting: older AMI")
            return False

        # if cluster leader, then accept as this will stick around
        if is_leader:
            CloudHost.log_debug("Accepting: cluster leader")
            return True

        # if only instance, accept
        if len(cluster_load) < 1:
            CloudHost.log_debug("Accepting: only instance (new AMI)")
            return True

        if avg_load >= 50:
            if self_load >= avg_load:
                CloudHost.log_debug("Accepting: not least loaded (self load >= avg)")
                return True

            # exclude machines with load >= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v < avg_load]
        else:
            filtered_nodes = cluster_load.keys()

        # at low load values, sorting by load will be inaccurate, sort alphabetically instead
        filtered_nodes.sort()
        if filtered_nodes[0] == CloudHost.instance_id():
            CloudHost.log_debug("Accepting: top among sorted instances (%r)", filtered_nodes)
            return True

        CloudHost.log_debug("Not accepting: not at top among sorted instances (%r)", filtered_nodes)
        return False

    @staticmethod
    def get_instance_stats(instance, stat_name, namespace=None):
        if (instance == CloudHost.instance_id()) and (stat_name in CloudHost.SELF_STATS):
            CloudHost.log_debug("Using cached self_stats. %s=%r", stat_name, CloudHost.SELF_STATS[stat_name])
            return CloudHost.SELF_STATS[stat_name]
        elif not CloudHost.ENABLED['cloudwatch']:
            return None

        if namespace is None:
            namespace = CloudHost.INSTALL_ID
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(minutes=30)
        res = None
        results = CloudHost.connect_cloudwatch().get_metric_statistics(60, start, end, stat_name, namespace,
                                                                       'Average', {'InstanceID': [instance]})
        for _res in results:
            if (res is None) or (res['Timestamp'] < _res['Timestamp']):
                res = _res
        return res['Average'] if res else None

    @staticmethod
    def get_cluster_average_stats(stat_name, namespace=None, results=None):
        if results is None:
            results = CloudHost.get_cluster_stats(stat_name, namespace)

        vals = results.values()
        if len(vals) > 0:
            return float(sum(vals)) / len(vals)
        return None

    @staticmethod
    def get_autoscale_group(gname):
        conn = CloudHost.connect_autoscale()
        try:
            groups = conn.get_all_groups([gname])
            if len(groups) > 0:
                return groups[0]
        except Exception:
            CloudHost.log_error("Exception getting autoscale group %s", gname)

        return None

    @staticmethod
    def get_autoscaled_instances(gname=None):
        if gname is None:
            gname = CloudHost.AUTOSCALE_GROUP
        group = CloudHost.get_autoscale_group(gname)
        if (group is None) or (len(group.instances) == 0):
            return []
        instances_ids = [i.instance_id for i in group.instances]
        reservations = CloudHost.connect_ec2().get_all_reservations(instances_ids)
        instances = [i.id for r in reservations for i in r.instances]
        return instances

    @staticmethod
    def get_ami_recentness(instance=None):
        if not CloudHost.ENABLED['autoscale']:
            return 0
        instances = CloudHost.get_autoscaled_instances()
        if instances is None:
            return 0
        max_ami_ver = 0
        min_ami_ver = sys.maxint
        for inst in instances:
            ami_ver = CloudHost.image_version(inst)
            max_ami_ver = max(max_ami_ver, ami_ver)
            min_ami_ver = min(min_ami_ver, ami_ver)

        if instance is None:
            instance = CloudHost.instance_id()
        self_ami_ver = CloudHost.image_version(instance)
        CloudHost.log_debug("ami versions: max: %d, min: %d, self(%s):%d", max_ami_ver, min_ami_ver,
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
    def get_cluster_stats(stat_name, namespace=None):
        if not CloudHost.ENABLED['cloudwatch']:
            if stat_name in CloudHost.SELF_STATS:
                return {CloudHost.instance_id(): CloudHost.SELF_STATS[stat_name]}
            else:
                return None

        dims = CloudHost.get_metric_dimensions(stat_name, namespace)
        if dims is None:
            return None

        if CloudHost.ENABLED['autoscale']:
            instances = CloudHost.get_autoscaled_instances()
        else:
            instances = None

        stats = {}
        if 'InstanceID' in dims:
            for instance in dims['InstanceID']:
                if (instances is None) or (instance in instances):
                    instance_load = CloudHost.get_instance_stats(instance, stat_name, namespace)
                    if instance_load is not None:
                        stats[instance] = instance_load

        return stats

    @staticmethod
    def push_file_to_s3(bucket, local_file, metadata=None):
        if not CloudHost.ENABLED['s3']:
            return None

        key_name = os.path.basename(local_file)
        k = Key(CloudHost.connect_s3_bucket(bucket))
        k.key = key_name
        if metadata is not None:
            for meta_name, meta_value in metadata.iteritems():
                k.set_metadata(meta_name, meta_value)
        k.set_contents_from_filename(local_file)
        return k

    @staticmethod
    def pull_file_from_s3(bucket, local_file, metadata_only=False):
        if not CloudHost.ENABLED['s3']:
            return None

        key_name = os.path.basename(local_file)
        k = CloudHost.connect_s3_bucket(bucket).get_key(key_name)
        if (k is not None) and (not metadata_only):
            k.get_contents_to_filename(local_file)
        return k

    @staticmethod
    def del_file_from_s3(bucket, local_file):
        if not CloudHost.ENABLED['s3']:
            return None

        key_name = os.path.basename(local_file)
        k = CloudHost.connect_s3_bucket(bucket).delete_key(key_name)
        return k

    @staticmethod
    def copy_file_in_s3(from_file, to_file, from_bucket, to_bucket=None):
        if not CloudHost.ENABLED['s3']:
            return None

        if to_bucket is None:
            to_bucket = from_bucket

        from_key_name = os.path.basename(from_file)
        to_key_name = os.path.basename(to_file)

        k = CloudHost.connect_s3_bucket(from_bucket).get_key(from_key_name)
        if k is None:
            return None
        k_new = k.copy(to_bucket, to_key_name)
        return k_new

    @staticmethod
    def move_file_in_s3(from_file, to_file, from_bucket, to_bucket=None):
        if not CloudHost.ENABLED['s3']:
            return None

        k_new = CloudHost.copy_file_in_s3(from_file, to_file, from_bucket, to_bucket)
        if k_new is None:
            return None
        CloudHost.del_file_from_s3(from_bucket, from_file)
        return k_new

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
        return CloudHost._state_check(resource, state)

    @staticmethod
    @retry(15, 0.5, backoff=1.5)
    def _wait_for_status_extended(resource, state):
        return CloudHost._state_check(resource, state)

    @staticmethod
    def get_email_rates():
        resp = CloudHost.connect_ses().get_send_quota()
        quota = resp['GetSendQuotaResponse']['GetSendQuotaResult']
        max_24_hrs = int(float(quota['Max24HourSend']))
        used_24_hrs = int(float(quota['SentLast24Hours']))
        max_rate_per_sec = int(float(quota['MaxSendRate']))
        return max_24_hrs-used_24_hrs, max_rate_per_sec

    @staticmethod
    def send_email(rcpt, sender, subject, body):
        CloudHost.connect_ses().send_email(source=sender,
                                           subject=subject,
                                           body=body,
                                           to_addresses=[rcpt])
