import datetime
import os
import pytz
import stat
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
import sh
import time

from jbox_util import LoggerMixin, parse_iso_time, retry


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
                CloudHost.INSTANCE_ID = 'localhost'
            else:
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
    def configure(has_s3=True, has_dynamodb=True, has_cloudwatch=True, has_autoscale=True,
                  has_route53=True, has_ebs=True, has_ses=True,
                  scale_up_at_load=80, scale_up_policy=None, autoscale_group=None,
                  route53_domain=None,
                  region='us-east-1', install_id='JuliaBox'):
        CloudHost.ENABLED['s3'] = has_s3
        CloudHost.ENABLED['dynamodb'] = has_dynamodb
        CloudHost.ENABLED['cloudwatch'] = has_cloudwatch
        CloudHost.ENABLED['autoscale'] = has_autoscale
        CloudHost.ENABLED['route53'] = has_route53
        CloudHost.ENABLED['ebs'] = has_ebs
        CloudHost.ENABLED['ses'] = has_ses

        CloudHost.SCALE_UP_AT_LOAD = scale_up_at_load
        CloudHost.SCALE_UP_POLICY = scale_up_policy
        CloudHost.AUTOSCALE_GROUP = autoscale_group

        CloudHost.ROUTE53_DOMAIN = route53_domain

        CloudHost.INSTALL_ID = install_id
        CloudHost.REGION = region

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
            if next_token is None:
                break
        if len(dims) == 0:
            CloudHost.log_info("invalid metric " + '.'.join([metric_namespace, metric_name]))
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
                CloudHost.log_info("Requesting scale up as cluster average load %r > %r",
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
    def get_autoscaled_instances():
        group = CloudHost.connect_autoscale().get_all_groups([CloudHost.AUTOSCALE_GROUP])[0]
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
    def _get_block_device_mapping(instance_id):
        maps = CloudHost.connect_ec2().get_instance_attribute(instance_id=instance_id,
                                                                attribute='blockDeviceMapping')['blockDeviceMapping']
        idmap = {}
        for dev_path, dev in maps.iteritems():
            idmap[dev_path] = dev.volume_id
        return idmap

    @staticmethod
    def _mount_device(dev_id, mount_dir):
        t1 = time.time()
        device = os.path.join('/dev', dev_id)
        mount_point = os.path.join(mount_dir, dev_id)
        actual_mount_point = CloudHost._get_mount_point(dev_id)
        if actual_mount_point == mount_point:
            return
        elif actual_mount_point is None:
            CloudHost.log_debug("Mounting device " + device + " at " + mount_point)
            res = sh.mount(mount_point)  # the mount point must be mentioned in fstab file
            if res.exit_code != 0:
                raise Exception("Failed to mount device " + device + " at " + mount_point)
        else:
            raise Exception("Device already mounted at " + actual_mount_point)
        tdiff = int(time.time() - t1)
        CloudHost.publish_stats("EBSMountTime", "Count", tdiff)

    @staticmethod
    def _get_volume(vol_id):
        vols = CloudHost.connect_ec2().get_all_volumes([vol_id])
        if len(vols) == 0:
            return None
        return vols[0]

    @staticmethod
    def _get_volume_attach_info(vol_id):
        vol = CloudHost._get_volume(vol_id)
        if vol is None:
            return None, None
        att = vol.attach_data
        return att.instance_id, att.device

    @staticmethod
    def unmount_device(dev_id, mount_dir):
        mount_point = os.path.join(mount_dir, dev_id)
        actual_mount_point = CloudHost._get_mount_point(dev_id)
        if actual_mount_point is None:
            return  # not mounted
        t1 = time.time()
        CloudHost.log_debug("Unmounting dev_id:" + repr(dev_id) +
                            " mount_point:" + repr(mount_point) +
                            " actual_mount_point:" + repr(actual_mount_point))
        if mount_point != actual_mount_point:
            CloudHost.log_info("Mount point expected:" + mount_point + ", got:" + repr(actual_mount_point))
            mount_point = actual_mount_point
        res = sh.umount(mount_point)  # the mount point must be mentioned in fstab file
        if res.exit_code != 0:
            raise Exception("Device could not be unmounted from " + mount_point)
        tdiff = int(time.time() - t1)
        CloudHost.publish_stats("EBSUnmountTime", "Count", tdiff)

    @staticmethod
    def _get_mount_point(dev_id):
        device = os.path.join('/dev', dev_id)
        for line in sh.mount():
            if line.startswith(device):
                return line.split()[2]
        return None

    @staticmethod
    def _state_check(obj, state):
        obj.update()
        classname = obj.__class__.__name__
        if classname in ('Snapshot', 'Volume'):
            return obj.status == state
        else:
            return obj.state == state

    @staticmethod
    def _device_exists(dev):
        try:
            mode = os.stat(dev).st_mode
        except OSError:
            return False
        return stat.S_ISBLK(mode)

    @staticmethod
    @retry(10, 0.5, backoff=1.5)
    def _wait_for_status(resource, state):
        return CloudHost._state_check(resource, state)

    @staticmethod
    @retry(15, 0.5, backoff=1.5)
    def _wait_for_status_extended(resource, state):
        return CloudHost._state_check(resource, state)

    @staticmethod
    @retry(10, 0.5, backoff=1.5)
    def _wait_for_device(dev):
        return CloudHost._device_exists(dev)

    @staticmethod
    def _ensure_volume_available(vol_id, force_detach=False):
        conn = CloudHost.connect_ec2()
        vol = CloudHost._get_volume(vol_id)
        if vol is None:
            raise Exception("Volume not found: " + vol_id)

        if CloudHost._state_check(vol, 'available'):
            return True

        # volume may be attached
        instance_id = CloudHost.instance_id()
        att_instance_id, att_device = CloudHost._get_volume_attach_info(vol_id)

        if (att_instance_id is None) or (att_instance_id == instance_id):
            return True

        if force_detach:
            CloudHost.log_info("Forcing detach of volume " + vol_id)
            conn.detach_volume(vol_id)
            CloudHost._wait_for_status(vol, 'available')

        if not CloudHost._state_check(vol, 'available'):
            raise Exception("Volume not available: " + vol_id +
                            ", attached to: " + att_instance_id +
                            ", state: " + vol.status)

    @staticmethod
    def _attach_free_volume(vol_id, dev_id, mount_dir):
        conn = CloudHost.connect_ec2()
        instance_id = CloudHost.instance_id()
        device = os.path.join('/dev', dev_id)
        mount_point = os.path.join(mount_dir, dev_id)
        vol = CloudHost._get_volume(vol_id)

        CloudHost.log_info("Attaching volume " + vol_id + " at " + device)
        t1 = time.time()
        conn.attach_volume(vol_id, instance_id, device)

        if not CloudHost._wait_for_status(vol, 'in-use'):
            CloudHost.log_error("Could not attach volume " + vol_id)
            raise Exception("Volume could not be attached. Volume id: " + vol_id)

        if not CloudHost._wait_for_device(device):
            CloudHost.log_error("Could not attach volume " + vol_id + " to device " + device)
            raise Exception("Volume could not be attached. Volume id: " + vol_id + ", device: " + device)
        tdiff = int(time.time() - t1)
        CloudHost.publish_stats("EBSAttachTime", "Count", tdiff)

        CloudHost._mount_device(dev_id, mount_dir)
        return device, mount_point

    @staticmethod
    def _get_mapped_volumes(instance_id=None):
        if instance_id is None:
            instance_id = CloudHost.instance_id()

        return CloudHost.connect_ec2().get_instance_attribute(instance_id=instance_id,
                                                              attribute='blockDeviceMapping')['blockDeviceMapping']

    @staticmethod
    def get_volume_id_from_device(dev_id):
        device = os.path.join('/dev', dev_id)
        maps = CloudHost._get_mapped_volumes()
        CloudHost.log_debug("Devices mapped: " + repr(maps))
        if device not in maps:
            return None
        return maps[device].volume_id

    @staticmethod
    def is_snapshot_complete(snap_id):
        snaps = CloudHost.connect_ec2().get_all_snapshots([snap_id])
        if len(snaps) == 0:
            raise Exception("Snapshot not found with id " + str(snap_id))
        snap = snaps[0]
        return snap.status == 'completed'

    @staticmethod
    def get_snapshot_age(snap_id):
        snaps = CloudHost.connect_ec2().get_all_snapshots([snap_id])
        if len(snaps) == 0:
            raise Exception("Snapshot not found with id " + str(snap_id))
        snap = snaps[0]

        st = parse_iso_time(snap.start_time)
        nt = datetime.datetime.now(pytz.utc)
        return nt - st

    @staticmethod
    def create_new_volume(snap_id, dev_id, mount_dir, tag=None):
        CloudHost.log_info("Creating volume with tag " + tag +
                           " from snapshot " + snap_id +
                           " at dev_id " + dev_id +
                           " mount_dir " + mount_dir)
        conn = CloudHost.connect_ec2()
        disk_sz_gb = 1
        vol = conn.create_volume(disk_sz_gb, CloudHost.zone(),
                                 snapshot=snap_id,
                                 volume_type='gp2')
                                 # volume_type='io1',
                                 # iops=30*disk_sz_gb)
        CloudHost._wait_for_status(vol, 'available')
        vol_id = vol.id
        CloudHost.log_info("Created volume with id " + vol_id)

        if tag is not None:
            conn.create_tags([vol_id], {"Name": tag})
            CloudHost.log_info("Added tag " + tag + " to volume with id " + vol_id)

        mnt_info = CloudHost._attach_free_volume(vol_id, dev_id, mount_dir)
        return mnt_info[0], mnt_info[1], vol_id

    # @staticmethod
    # def detach_mounted_volume(dev_id, mount_dir, delete=False):
    #     CloudHelper.log_info("Detaching volume mounted at device " + dev_id)
    #     vol_id = CloudHelper.get_volume_id_from_device(dev_id)
    #     CloudHelper.log_debug("Device " + dev_id + " maps volume " + vol_id)
    #
    #     # find the instance and device to which the volume is mapped
    #     instance, device = CloudHelper._get_volume_attach_info(vol_id)
    #     if instance is None:  # the volume is not mounted
    #         return
    #
    #     # if mounted to current instance, also unmount the device
    #     if instance == CloudHelper.instance_id():
    #         dev_id = device.split('/')[-1]
    #         CloudHelper.unmount_device(dev_id, mount_dir)
    #         time.sleep(1)
    #
    #     return CloudHelper.detach_volume(vol_id, delete=delete)

    @staticmethod
    def detach_volume(vol_id, delete=False):
        # find the instance and device to which the volume is mapped
        instance, device = CloudHost._get_volume_attach_info(vol_id)
        conn = CloudHost.connect_ec2()
        if instance is not None:  # the volume is attached
            CloudHost.log_debug("Detaching " + vol_id + " from instance " + instance + " device " + repr(device))
            vol = CloudHost._get_volume(vol_id)
            t1 = time.time()
            conn.detach_volume(vol_id, instance, device)
            if not CloudHost._wait_for_status_extended(vol, 'available'):
                raise Exception("Volume could not be detached " + vol_id)
            tdiff = int(time.time() - t1)
            CloudHost.publish_stats("EBSDetachTime", "Count", tdiff)
        if delete:
            CloudHost.log_debug("Deleting " + vol_id)
            conn.delete_volume(vol_id)

    @staticmethod
    def attach_volume(vol_id, dev_id, mount_dir, force_detach=False):
        """
        In order for EBS volumes to be mountable on the host system, JuliaBox relies on the fstab file must have
        pre-filled mount points with options to allow non-root user to mount/unmount them. This necesseciates that
        the mount point and device ids association be fixed beforehand. So we follow a convention where /dev/dev_id
        will be mounted at /mount_dir/dev_id

        Returns the device path and mount path where the volume was attached.

        If the volume is already mounted on the current instance, the existing device and mount paths are returned,
        which may be different from what was requested.

        :param vol_id: EBS volume id to mount
        :param dev_id: volume will be attached at /dev/dev_id
        :param mount_dir: device will be mounted at /mount_dir/dev_id
        :param force_detach: detach the volume from any other instance that might have attached it
        :return: device_path, mount_path
        """
        CloudHost.log_info("Attaching volume " + vol_id + " to dev_id " + dev_id + " at " + mount_dir)
        CloudHost._ensure_volume_available(vol_id, force_detach=force_detach)
        att_instance_id, att_device = CloudHost._get_volume_attach_info(vol_id)

        if att_instance_id is None:
            return CloudHost._attach_free_volume(vol_id, dev_id, mount_dir)
        else:
            CloudHost.log_info("Volume " + vol_id + " already attached to " + att_instance_id + " at " + att_device)
            CloudHost._mount_device(dev_id, mount_dir)
            return att_device, mount_dir

    @staticmethod
    def snapshot_volume(vol_id=None, dev_id=None, tag=None, description=None, wait_till_complete=True):
        if dev_id is not None:
            vol_id = CloudHost.get_volume_id_from_device(dev_id)
        if vol_id is None:
            CloudHost.log_info("No volume to snapshot. vol_id: " + repr(vol_id) + ", dev_id: " + repr(dev_id))
            return
        vol = CloudHost._get_volume(vol_id)
        CloudHost.log_info("Creating snapshot for volume: " + vol_id)
        snap = vol.create_snapshot(description)
        if wait_till_complete and (not CloudHost._wait_for_status_extended(snap, 'completed')):
            raise Exception("Could not create snapshot for volume " + vol_id)
        CloudHost.log_info("Created snapshot " + snap.id + " for volume " + vol_id)
        if tag is not None:
            CloudHost.connect_ec2().create_tags([snap.id], {'Name': tag})
        return snap.id

    @staticmethod
    def delete_snapshot(snapshot_id):
        CloudHost.connect_ec2().delete_snapshot(snapshot_id)

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
