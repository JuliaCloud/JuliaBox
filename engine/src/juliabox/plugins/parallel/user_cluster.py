__author__ = 'tan'
import datetime
import pytz

from juliabox.db import JBoxDynConfig
from juliabox.plugins.compute_ec2 import Cluster, CompEC2
from juliabox.jbox_util import LoggerMixin, unique_sessname


class SpotPriceCache(LoggerMixin):
    CACHE = {}
    SPOT_PRICE_REFETCH_SECS = 5*60  # 5 minutes

    @staticmethod
    def get(instance_type):
        nowtime = datetime.datetime.now(pytz.utc)
        cached = None

        if instance_type in SpotPriceCache.CACHE:
            cached = SpotPriceCache.CACHE[instance_type]
            if (cached['time'] - nowtime).total_seconds() < SpotPriceCache.SPOT_PRICE_REFETCH_SECS:
                cached = None

        if cached is None:
            newprices = Cluster.get_spot_price(instance_type)
            cached = {
                'time': nowtime,
                'prices': newprices
            }
            SpotPriceCache.CACHE[instance_type] = cached

        return cached['prices']


class UserCluster(LoggerMixin):
    IMAGE_ID = None
    INSTANCE_TYPE = None
    INSTANCE_CORES = None
    INSTANCE_COST = None
    KEY_NAME = None
    SEC_GRPS = None
    CONFIGURE_TIME = None
    RECONF_SECS = 10*60           # 10 minutes
    NAME_PFX = 'jc_'

    def __init__(self, user_email, gname=None):
        UserCluster.configure_dynamic()
        self.user_email = user_email

        if gname is None:
            self.gname = UserCluster.NAME_PFX + unique_sessname(user_email)
        else:
            self.gname = gname

        if user_email is not None:
            self._dbg_str = ("UserCluster(%s - %s)" % (user_email, self.gname))
        else:
            self._dbg_str = ("UserCluster(%s)" % (self.gname,))

        self.placement_group = None
        self.autoscale_group = None
        self.launch_config = None
        self.instances = []
        self.public_ips = []
        self.public_hosts = []
        self.private_ips = []
        self.private_hosts = []

    @staticmethod
    def sessname_for_cluster(gname):
        if gname.startswith(UserCluster.NAME_PFX):
            return gname[len(UserCluster.NAME_PFX):]
        return None

    @staticmethod
    def configure_dynamic():
        nowtime = datetime.datetime.now(pytz.utc)
        if UserCluster.CONFIGURE_TIME is None:
            refetch = True
        else:
            tdiff = (nowtime - UserCluster.CONFIGURE_TIME).total_seconds()
            refetch = tdiff > UserCluster.RECONF_SECS

        if refetch:
            cfg = JBoxDynConfig.get_user_cluster_config(CompEC2.INSTALL_ID)
            UserCluster.IMAGE_ID = cfg['image_id']
            UserCluster.INSTANCE_TYPE = cfg['instance_type']
            UserCluster.INSTANCE_CORES = cfg['instance_cores']
            UserCluster.INSTANCE_COST = cfg['instance_cost']
            UserCluster.KEY_NAME = cfg['key_name']
            UserCluster.SEC_GRPS = cfg['sec_grps']
            UserCluster.CONFIGURE_TIME = nowtime

    # @staticmethod
    # def configure(image_id, instance_type, instance_cores, instance_cost, key_name, sec_grps):
    #     UserCluster.IMAGE_ID = image_id
    #     UserCluster.INSTANCE_TYPE = instance_type
    #     UserCluster.INSTANCE_CORES = instance_cores
    #     UserCluster.INSTANCE_COST = instance_cost
    #     UserCluster.KEY_NAME = key_name
    #     UserCluster.SEC_GRPS = sec_grps
    #     UserCluster.CONFIGURE_TIME = datetime.datetime.now(pytz.utc)

    @staticmethod
    def get_best_spot():
        prices = SpotPriceCache.get(UserCluster.INSTANCE_TYPE)
        # get the best location based on median price only for now
        minprice = None
        minloc = None
        for loc, price in prices.iteritems():
            if minloc is None:
                minloc = loc
                minprice = price
            elif minprice['median'] > price['median']:
                minloc = loc
                minprice = price
        return minloc, minprice

    @staticmethod
    def get_default_instance_spec():
        minloc, minprice = UserCluster.get_best_spot()
        return {
            'image_id': UserCluster.IMAGE_ID,
            'instance_type': UserCluster.INSTANCE_TYPE,
            'instance_cores': UserCluster.INSTANCE_CORES,
            'instance_cost': UserCluster.INSTANCE_COST,
            'instance_loc': minloc,
            'instance_cost_range': minprice
        }

    def get_instance_spec(self):
        if self.exists():
            # get cost from launch spec
            spot_price = self.launch_config.spot_price if self.launch_config else None
            price = spot_price if spot_price else UserCluster.INSTANCE_COST
            count = len(self.instances)
            desired_count = self.autoscale_group.desired_capacity if self.autoscale_group else 0
            return {
                'instance_cost': price,
                'count': count,
                'desired_count': desired_count
            }
        else:
            return None

    def status(self):
        exists = self.exists()
        inerror = exists and ((self.autoscale_group is None) or
                              (self.launch_config is None) or
                              (self.placement_group is None))
        cluster_state = self.get_instance_spec()
        configuration = UserCluster.get_default_instance_spec()
        return {
            'config': configuration,
            'exists': exists,
            'inerror': inerror,
            'instances': cluster_state
        }

    def debug_str(self):
        return self._dbg_str

    def exists(self):
        self.placement_group = Cluster.get_placement_group(self.gname)
        self.autoscale_group = Cluster.get_autoscale_group(self.gname)
        self.launch_config = Cluster.get_launch_config(self.gname)
        self.refresh_instances()

        self.log_debug("%s - placement_group:%r, autoscale_group:%r, launch_config:%r, count:%d",
                       self.debug_str(),
                       (self.placement_group is not None),
                       (self.launch_config is not None),
                       (self.autoscale_group is not None),
                       len(self.instances))

        return ((self.placement_group is not None)
                or (self.launch_config is not None)
                or (self.autoscale_group is not None))

    def refresh_instances(self):
        self.instances = Cluster.get_autoscaled_instances(self.gname)
        self.public_ips = Cluster.get_public_ips_by_placement_group(self.gname)
        self.public_hosts = Cluster.get_public_hostnames_by_placement_group(self.gname)
        self.private_ips = Cluster.get_private_ips_by_placement_group(self.gname)
        self.private_hosts = Cluster.get_private_hostnames_by_placement_group(self.gname)

    def create(self, ninsts, avzone, user_data, spot_price=0):
        if self.exists():
            raise Exception("%s exists" % (self.debug_str(),))

        # create a placement group
        placement_group = Cluster.create_placement_group(self.gname)
        if not placement_group:
            self.log_error("%s - Error creating placement group", self.debug_str())
            raise Exception("Error creating placement group")

        # create a launch configuration
        Cluster.create_launch_config(self.gname, UserCluster.IMAGE_ID, UserCluster.INSTANCE_TYPE,
                                     UserCluster.KEY_NAME, UserCluster.SEC_GRPS,
                                     user_data=user_data,
                                     spot_price=spot_price)
        self.log_info("Launch configuration %s", self.gname)

        # create an autoscale group
        agrp = Cluster.create_autoscale_group(self.gname, self.gname, self.gname, ninsts, [avzone])
        if agrp is None:
            self.log_error("%s - Error creating autoscale group", self.debug_str())
            raise Exception("Error creating placement group")

        self.log_info("Autoscaling group %r", agrp)
        self.exists()

    @staticmethod
    def list_all():
        ascale_conn = Cluster._autoscale()

        pgrps = [x for x in Cluster.get_placement_groups() if x.name.startswith(UserCluster.NAME_PFX)]
        UserCluster.log_info("%d placement groups", len(pgrps))
        for grp in pgrps:
            UserCluster.log_info("\t%s, %s, %s", grp.name, grp.strategy, repr(grp.state))

        configs = [x for x in ascale_conn.get_all_launch_configurations() if x.name.startswith(UserCluster.NAME_PFX)]
        UserCluster.log_info("%d launch configurations", len(configs))
        for config in configs:
            UserCluster.log_info("\t%s", config.name)

        agrps = [x for x in ascale_conn.get_all_groups() if x.name.startswith(UserCluster.NAME_PFX)]
        UserCluster.log_info("%d autoscale groups", len(agrps))
        for grp in agrps:
            UserCluster.log_info("\t%s", grp.name)

        return pgrps, configs, agrps

    @staticmethod
    def list_all_groupids():
        groupids = set()
        for entity in UserCluster.list_all():
            for item in entity:
                groupids.add(item.name)
        return groupids

    def delete(self):
        if not self.exists():
            return

        if len(self.instances) > 0:
            raise Exception("Can not delete %s with %d active instances" % (self.debug_str(), len(self.instances)))

        Cluster.delete_autoscale_group(self.gname)
        Cluster.delete_launch_config(self.gname)
        Cluster.delete_placement_group(self.gname)

    def set_capacity(self, ninst):
        conn = Cluster._autoscale()
        conn.set_desired_capacity(self.gname, ninst, False)

    def start(self):
        self.set_capacity(self.autoscale_group.max_size)

    def terminate(self):
        self.set_capacity(0)

    def isactive(self):
        if not self.exists():
            return False

        if len(self.instances) > 0:
            return True
        if self.autoscale_group and (self.autoscale_group.desired_capacity > 0):
            return True

        return False

    def terminate_or_delete(self):
        if self.isactive():
            self.terminate()
        else:
            self.delete()
