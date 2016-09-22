__author__ = 'Nishanth'

import datetime
import sys
import pytz
import requests
import re
import json
import socket
import time
import threading

from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials

from juliabox.cloud import JBPluginCloud
from juliabox.db import JBPluginDB
from juliabox.jbox_util import JBoxCfg, parse_iso_time, retry, retry_on_errors
from juliabox.db import JBoxInstanceProps

class CompGCE(JBPluginCloud):
    provides = [JBPluginCloud.JBP_COMPUTE, JBPluginCloud.JBP_COMPUTE_GCE]
    threadlocal = threading.local()
    ZONE = None
    INSTALL_ID = None

    AUTOSCALE_GROUP = None
    SCALE_UP_POLICY = None
    SCALE_UP_AT_LOAD = 80
    SCALE_UP_INTERVAL = 300

    INSTANCE_ID = None
    INSTANCE_IMAGE_VERS = {}

    PUBLIC_HOSTNAME = None
    LOCAL_HOSTNAME = None
    LOCAL_IP = None
    PUBLIC_IP = None

    GOOGLE_HEADERS = {"Metadata-Flavor": "Google"}    # HTTP header for querying metadata
    THIS_METADATA = None    # Metadata of current instance

    MIN_UPTIME = 50
    MONITORING_PLUGIN = None

    @staticmethod
    def configure():
        CompGCE.SCALE_UP_AT_LOAD = JBoxCfg.get('cloud_host.scale_up_at_load', 80)
        CompGCE.SCALE_UP_POLICY = JBoxCfg.get('cloud_host.scale_up_policy', None)
        CompGCE.AUTOSCALE_GROUP = JBoxCfg.get('cloud_host.autoscale_group', None)
        CompGCE.INSTALL_ID = JBoxCfg.get('cloud_host.install_id', None)
        CompGCE.MIN_UPTIME = JBoxCfg.get('cloud_host.min_uptime', 50)
        CompGCE.SCALE_UP_INTERVAL = JBoxCfg.get('cloud_host.scale_up_interval', 300)

    @staticmethod
    def get_install_id():
        return CompGCE.INSTALL_ID

    @staticmethod
    def _get_this_instance_metadata():
        if CompGCE.THIS_METADATA == None:
            CompGCE.THIS_METADATA = json.loads(requests.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/?recursive=true",
                headers=CompGCE.GOOGLE_HEADERS).text)
        return CompGCE.THIS_METADATA

    @staticmethod
    def get_instance_id():
        if CompGCE.INSTANCE_ID is None:
            CompGCE.INSTANCE_ID = socket.gethostname()
        return CompGCE.INSTANCE_ID

    @staticmethod
    def get_monitoring_plugin():
        if CompGCE.MONITORING_PLUGIN == None:
            CompGCE.MONITORING_PLUGIN = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_MONITORING_GOOGLE)
        return CompGCE.MONITORING_PLUGIN

    @staticmethod
    def _make_alias_hostname(instance_id=None):
        dns_name = CompGCE.get_instance_id() if instance_id is None else instance_id
        if CompGCE.AUTOSCALE_GROUP is not None:
            dns_name += ('-' + CompGCE.AUTOSCALE_GROUP)
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_DNS)
        dns_name += ('.' + plugin.domain())

        return dns_name

    @staticmethod
    def get_alias_hostname():
        plugin = JBPluginCloud.jbox_get_plugin(JBPluginCloud.JBP_DNS)
        if plugin is None:
            return CompGCE.get_instance_public_hostname()
        return CompGCE._make_alias_hostname()

    @staticmethod
    def get_instance_public_hostname(instance_name=None):
        # GCE instances have no public hostname, hence returning public IP address
        if instance_name is None:
            if CompGCE.PUBLIC_HOSTNAME is None:
                CompGCE.PUBLIC_HOSTNAME = CompGCE.get_instance_public_ip()
            return CompGCE.PUBLIC_HOSTNAME
        else:
            attrs = CompGCE._instance_attrs(instance_name)
            return attrs["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

    @staticmethod
    def get_instance_local_hostname(instance_name=None):
        if instance_name is None:
            if CompGCE.LOCAL_HOSTNAME is None:
                CompGCE.LOCAL_HOSTNAME = CompGCE._get_this_instance_metadata()["hostname"]
            return CompGCE.LOCAL_HOSTNAME
        else:
            # Cant find a way to get local hostname returning local IP addr for now.
            attrs = CompGCE._instance_attrs(instance_name)
            return attrs['networkInterfaces'][0]['networkIP']

    @staticmethod
    def get_instance_public_ip(instance_name=None):
        if instance_name is None:
            if CompGCE.PUBLIC_IP is None:
                CompGCE.PUBLIC_IP = CompGCE._get_this_instance_metadata()["networkInterfaces"][0]["accessConfigs"][0]["externalIp"]
            return CompGCE.PUBLIC_IP
        else:
            attrs = CompGCE._instance_attrs(instance_name)
            return attrs["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

    @staticmethod
    def get_instance_local_ip(instance_name=None):
        if instance_name is None:
            if CompGCE.LOCAL_IP is None:
                CompGCE.LOCAL_IP = CompGCE._get_this_instance_metadata()["networkInterfaces"][0]["ip"]
            return CompGCE.LOCAL_IP
        else:
            attrs = CompGCE._instance_attrs(instance_name)
            return attrs['networkInterfaces'][0]['networkIP']

    @staticmethod
    def get_cluster_average_stats(stat_name, namespace=None, results=None):
        if results is None:
            results = CompGCE.get_cluster_stats(stat_name, namespace)

        vals = results.values()
        if len(vals) > 0 and vals[0] != None:
            return float(sum(vals)) / len(vals)
        return None

    @staticmethod
    @retry_on_errors(retries=2)
    def terminate_instance(instance=None):
        if instance is None:
            instance = CompGCE.get_instance_id()

        CompGCE.log_info("Terminating instance: %s", instance)
        try:
            insturl = 'zones/%s/instances/%s' % (CompGCE._zone(), instance)
            CompGCE._connect_gce().instanceGroupManagers().deleteInstances(
                project=CompGCE.INSTALL_ID, zone=CompGCE._zone(),
                instanceGroupManager=CompGCE.AUTOSCALE_GROUP,
                body={'instances': [insturl]}).execute()
        except:
            CompGCE.log_exception("Error terminating instance to scale down")

    @staticmethod
    def can_terminate(is_leader):
        uptime = CompGCE._uptime_minutes()

        # if uptime less than hour return false
        if uptime < CompGCE.MIN_UPTIME:
            CompGCE.log_debug("not terminating as uptime (%r) < %r",
                              uptime, CompGCE.MIN_UPTIME)
            return False

        # cluster leader stays
        if is_leader:
            CompGCE.log_debug("not terminating as this is the cluster leader")
            return False

        # older amis terminate while newer amis never terminate
        ami_recentness = CompGCE.get_image_recentness()
        CompGCE.log_debug("AMI recentness = %d", ami_recentness)
        if ami_recentness < 0:
            CompGCE.log_debug("Terminating because running an older AMI")
            return True
        elif ami_recentness > 0:
            CompGCE.log_debug("Not terminating because running a more recent AMI")
            return False

        # keep at least 1 machine running
        instances = CompGCE.get_all_instances()
        if len(instances) == 1:
            CompGCE.log_debug("not terminating as this is the only machine")
            return False

        return True

    @staticmethod
    def get_redirect_instance_id():
        cluster_load = CompGCE.get_cluster_stats('Load')
        cluster_load = {k: v for k, v in cluster_load.iteritems() if CompGCE.get_image_recentness(k) >= 0}
        avg_load = CompGCE.get_cluster_average_stats('Load', results=cluster_load)
        if avg_load == None:
            return CompGCE.get_instance_id()
        if avg_load >= 50:
            # exclude machines with load >= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v < avg_load]
        else:
            # exclude machines with load <= avg_load and load >= 100
            filtered_nodes = [k for k, v in cluster_load.iteritems() if 100 > v > avg_load]

            if len(filtered_nodes) == 0:
                # exclude the least loaded machine and machines with load >= 100
                least_load = min(cluster_load.values())
                filtered_nodes = [k for k, v in cluster_load.iteritems() if 100 > v > least_load]

            if len(filtered_nodes) == 0:
                # just remove machines loaded at 100%
                filtered_nodes = [k for k, v in cluster_load.iteritems() if 100 > v]

        if len(filtered_nodes) == 0:
            filtered_nodes = cluster_load.keys()

        filtered_nodes.sort()
        CompGCE.log_info("Redirect to instance_id: %r", filtered_nodes[0])
        return filtered_nodes[0]

    @staticmethod
    def should_accept_session(is_leader):
        self_instance_id = CompGCE.get_instance_id()
        self_load = CompGCE.get_instance_stats(self_instance_id, 'Load')
        CompGCE.log_debug("Self load: %r", self_load)

        cluster_load = CompGCE.get_cluster_stats('Load')
        CompGCE.log_debug("Cluster load: %r", cluster_load)

        # add self to cluster if not yet registered in cluster stats
        if self_instance_id not in cluster_load.keys():
            cluster_load[self_instance_id] = self_load

        # remove machines with older AMIs
        cluster_load = {k: v for k, v in cluster_load.iteritems() if CompGCE.get_image_recentness(k) >= 0}
        CompGCE.log_debug("Cluster load (excluding old amis): %r", cluster_load)

        avg_load = CompGCE.get_cluster_average_stats('Load', results=cluster_load)
        CompGCE.log_debug("Average load (excluding old amis): %r", avg_load)

        if avg_load >= CompGCE.SCALE_UP_AT_LOAD:
            CompGCE.log_warn("Requesting scale up as cluster average load %r > %r", avg_load, CompGCE.SCALE_UP_AT_LOAD)
            CompGCE._add_instance()

        if self_load >= 100:
            CompGCE.log_debug("Not accepting: fully loaded")
            return False

        # handle ami switchover. newer AMIs always accept, older AMIs always reject
        ami_recentness = CompGCE.get_image_recentness()
        CompGCE.log_debug("AMI recentness = %d", ami_recentness)
        if ami_recentness > 0:
            CompGCE.log_debug("Accepting: more recent AMI")
            return True
        elif ami_recentness < 0:
            CompGCE.log_debug("Not accepting: older AMI")
            return False

        # if cluster leader, then accept as this will stick around
        if is_leader:
            CompGCE.log_debug("Accepting: cluster leader")
            return True

        # if only instance, accept
        if len(cluster_load) < 1:
            CompGCE.log_debug("Accepting: only instance (new AMI)")
            return True

        filtered_nodes = []
        if avg_load >= 50:
            if self_load >= avg_load:
                CompGCE.log_debug("Accepting: not least loaded (self load >= avg)")
                return True

            # exclude machines with load >= avg_load
            filtered_nodes = [k for k, v in cluster_load.iteritems() if v < avg_load]

        if len(filtered_nodes) == 0:
            filtered_nodes = cluster_load.keys()

        # at low load values, sorting by load will be inaccurate, sort alphabetically instead
        filtered_nodes.sort()
        if filtered_nodes[0] == CompGCE.get_instance_id():
            CompGCE.log_debug("Accepting: top among sorted instances (%r)", filtered_nodes)
            return True

        CompGCE.log_debug("Not accepting: not at top among sorted instances (%r)", filtered_nodes)
        return False

    @staticmethod
    def _zone():
        if CompGCE.ZONE is None:
            CompGCE.ZONE = CompGCE._get_this_instance_metadata()["zone"].split('/')[-1]
        return CompGCE.ZONE

    @staticmethod
    @retry_on_errors(retries=2)
    def _get_instance_data(instname):
        conn = CompGCE._connect_gce().instances()
        inst = conn.get(project=CompGCE.INSTALL_ID, zone=CompGCE._zone(),
                        instance=instname).execute()
        return inst

    @staticmethod
    @retry_on_errors(retries=2)
    def _get_disk_data(diskname):
        conn = CompGCE._connect_gce().disks()
        disk = conn.get(project=CompGCE.INSTALL_ID, zone=CompGCE._zone(),
                        disk=diskname).execute()
        return disk

    @staticmethod
    def _ver_from_ami(aminame):
        a = aminame.split('-')[-1]
        ver = 0
        res = re.search(r'[a-z]*([0-9]+)[a-z]*', a)
        if res:
            ver = res.group(1)
        return int(ver)

    @staticmethod
    def _image_version(inst_id):
        try:
            if inst_id not in CompGCE.INSTANCE_IMAGE_VERS:
                inst = CompGCE._get_instance_data(inst_id)
                diskname = inst['disks'][0]['source'].split('/')[-1]
                disk = CompGCE._get_disk_data(diskname)
                aminame = disk['sourceImage']
                ver = CompGCE._ver_from_ami(aminame)
                CompGCE.INSTANCE_IMAGE_VERS[inst_id] = ver

            return CompGCE.INSTANCE_IMAGE_VERS[inst_id]
        except:
            CompGCE.log_exception("Exception finding image_version of %s", inst_id)
            return 0

    @staticmethod
    def _connect_gce():
        c = getattr(CompGCE.threadlocal, 'gce_conn', None)
        if c is None:
            creds = GoogleCredentials.get_application_default()
            CompGCE.threadlocal.gce_conn = c = build("compute", "v1",
                                                     credentials=creds)
        return c

    @staticmethod
    @retry_on_errors(retries=2)
    def _instance_attrs(instance_name=None):
        if instance_name is None:
            instance_name = CompGCE.get_instance_id()
        ins = CompGCE._connect_gce().instances()
        return ins.get(project=CompGCE.INSTALL_ID, zone=CompGCE._zone(),
                       instance=instance_name).execute()

    @staticmethod
    def _uptime_minutes(instance_name=None):
        attrs = CompGCE._instance_attrs(instance_name)
        lt = parse_iso_time(attrs["creationTimestamp"])
        nt = datetime.datetime.now(pytz.utc)
        uptime = nt - lt
        minutes = int(uptime.total_seconds()/60)
        return minutes

    @staticmethod
    @retry_on_errors(retries=2)
    def _get_instances(gname, only_running=False):
        conn = CompGCE._connect_gce().instanceGroups()
        flag = 'RUNNING' if only_running else 'ALL'
        data = conn.listInstances(project=CompGCE.INSTALL_ID, zone=CompGCE._zone(),
                                  body={'instanceState': flag},
                                  instanceGroup=gname).execute()
        ret = []
        for inst in data.get('items', []):
            ret.append(inst['instance'].split('/')[-1])
        return ret

    @staticmethod
    def get_all_instances(gname=None):
        if gname is None:
            gname = CompGCE.AUTOSCALE_GROUP
        if gname is None:
            return [CompGCE.get_instance_id()]
        instances = CompGCE._get_instances(gname, only_running=True)
        if len(instances) == 0:
            return [CompGCE.get_instance_id()]
        return instances

    @staticmethod
    @retry_on_errors(retries=2)
    def _increment_num_instances(num_instances):
        conn = CompGCE._connect_gce().instanceGroupManagers()
        curr = conn.get(project=CompGCE.INSTALL_ID, zone=CompGCE._zone(),
                        instanceGroupManager=CompGCE.AUTOSCALE_GROUP).execute()['targetSize']
        return conn.resize(project=CompGCE.INSTALL_ID, zone=CompGCE._zone(),
                           instanceGroupManager=CompGCE.AUTOSCALE_GROUP,
                           size=curr + num_instances).execute()

    DB_PLUGIN = None
    @staticmethod
    def _get_db_plugin():
        if not CompGCE.DB_PLUGIN:
            CompGCE.DB_PLUGIN = JBPluginDB.jbox_get_plugin(JBPluginDB.JBP_DB_CLOUDSQL)
        return CompGCE.DB_PLUGIN

    @staticmethod
    def _should_scale_up():
        plugin = CompGCE._get_db_plugin()
        conn = plugin.conn()
        c = conn.cursor()

        c.execute('SELECT * FROM scale_up_time')
        last_time = c.fetchone()[0]

        now = int(time.time())
        if now < last_time + CompGCE.SCALE_UP_INTERVAL:
            c.close()
            return False

        ret = c.execute('UPDATE scale_up_time SET scale_up_time = %d WHERE ' \
                        'scale_up_time = %d' % (now, last_time))
        conn.commit()
        c.close()
        if ret == 0:
            return False
        return True

    @staticmethod
    def _add_instance(num_instances=1):
        try:
            # Execute policy only after a reasonable wait period to let a new machine boot up.
            # This will prevent thrashing AWS APIs and triggering AWS throttling.
            # Cooldown policy can also apply after that.
            if CompGCE._should_scale_up():
                if CompGCE.SCALE_UP_POLICY == 'addinstance':
                    CompGCE._increment_num_instances(num_instances)
        except:
            CompGCE.log_exception("Error requesting scale up")

    @staticmethod
    def get_image_recentness(instance=None):
        instances = CompGCE.get_all_instances()
        if instances is None:
            return 0
        max_ami_ver = 0
        min_ami_ver = sys.maxint
        for inst in instances:
            ami_ver = CompGCE._image_version(inst)
            max_ami_ver = max(max_ami_ver, ami_ver)
            min_ami_ver = min(min_ami_ver, ami_ver)

        if instance is None:
            instance = CompGCE.get_instance_id()
        self_ami_ver = CompGCE._image_version(instance)
        CompGCE.log_debug("ami versions: max: %d, min: %d, self(%s):%d",
                          max_ami_ver, min_ami_ver, instance, self_ami_ver)
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
        return CompGCE._state_check(resource, state)

    @staticmethod
    @retry(15, 0.5, backoff=1.5)
    def _wait_for_status_extended(resource, state):
        return CompGCE._state_check(resource, state)

    @staticmethod
    def get_available_instances():
        JBoxInstanceProps.get_available_instances(CompGCE.get_install_id())

    @staticmethod
    def publish_stats(stat_name, stat_unit, stat_value):
        """ Publish custom cloudwatch statistics. Used for status monitoring and auto scaling. """
        CompGCE.publish_stats_multi([(stat_name, stat_unit, stat_value)])

    @staticmethod
    def publish_stats_multi(stats):
        CompGCE.get_monitoring_plugin().publish_stats_multi(stats, CompGCE.get_instance_id(),
                                                            CompGCE.get_instance_id(),
                                                            CompGCE.get_install_id(),
                                                            CompGCE.AUTOSCALE_GROUP)

    @staticmethod
    def get_instance_stats(instance, stat_name, namespace=None):
        if namespace == None:
            namespace = CompGCE.get_install_id()
        CompGCE.get_monitoring_plugin().get_instance_stats(instance, stat_name,
                                                           CompGCE.get_instance_id(),
                                                           namespace, CompGCE.AUTOSCALE_GROUP)

    @staticmethod
    def get_cluster_stats(stat_name, namespace=None):
        if namespace == None:
            namespace = CompGCE.INSTALL_ID
        dims = CompGCE.get_monitoring_plugin().get_metric_dimensions(stat_name, namespace,
                                                                     CompGCE.AUTOSCALE_GROUP)
        if dims is None:
            return None

        instances = CompGCE.get_all_instances()

        stats = {}
        if 'InstanceID' in dims:
            for instance in dims['InstanceID']:
                if (instances is None) or (instance in instances):
                    instance_load = CompGCE.get_instance_stats(instance, stat_name, namespace)
                    if instance_load is not None:
                        stats[instance] = instance_load

        return stats
