import datetime
import boto.ec2
import boto.ec2.cloudwatch
import boto.ec2.autoscale
import boto.route53
import boto.ses
from boto.ec2.autoscale import LaunchConfiguration, AutoScalingGroup
from boto.ec2.autoscale.tag import Tag
import boto.utils

from aws import CloudHost

class Cluster(CloudHost):
    @staticmethod
    def get_spot_price(inst_type, minutes=60):
        conn = CloudHost.connect_ec2()
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(minutes=minutes)

        next_token = None
        avzone_pricevals = {}
        avzone_pricestats = {}

        def median(lst):
            lst = sorted(lst)
            if len(lst) < 1:
                    return None
            if len(lst) %2 == 1:
                    return lst[((len(lst)+1)/2)-1]
            else:
                    return float(sum(lst[(len(lst)/2)-1:(len(lst)/2)+1]))/2.0

        def add_price(avzone, price):
            if avzone in avzone_pricevals:
                pricevals = avzone_pricevals[avzone]
            else:
                pricevals = []
                avzone_pricevals[avzone] = pricevals
            pricevals.append(price)

        while True:
            prices = conn.get_spot_price_history(instance_type=inst_type,
                                                 start_time=start.isoformat(), end_time=end.isoformat(),
                                                 next_token=next_token)
            for p in prices:
                add_price(p.availability_zone, p.price)
            next_token = prices.next_token
            if (next_token is None) or (len(next_token) == 0):
                break

        for avzone, prices in avzone_pricevals.iteritems():
            avzone_pricestats[avzone] = {
                'count': len(prices),
                'min': min(prices),
                'avg': sum(prices)/float(len(prices)),
                'median': median(prices),
                'max': max(prices)
            }

        return avzone_pricestats

    @staticmethod
    def terminate_by_placement_group(gname):
        conn = CloudHost.connect_ec2()
        instances = conn.get_only_instances(filters={"placement-group-name": gname, "instance-state-name": "running"})
        conn.terminate_instances(instance_ids=[i.id for i in instances])

    @staticmethod
    def get_placement_group(gname):
        existing = Cluster.get_placement_groups(gname)
        return existing if (existing is None) else existing[0]

    @staticmethod
    def get_placement_groups(gname=None):
        conn = CloudHost.connect_ec2()

        try:
            existing = conn.get_all_placement_groups(gname)
        except boto.exception.EC2ResponseError as ex:
            #print("\t%s" % (repr(ex),))
            return None

        if len(existing) == 0:
            return None
        return existing

    @staticmethod
    def create_placement_group(gname):
        if Cluster.get_placement_group(gname) is None:
            conn = CloudHost.connect_ec2()
            return conn.create_placement_group(gname, strategy='cluster')
        return True

    @staticmethod
    def delete_placement_group(gname):
        pgrp = Cluster.get_placement_group(gname)
        if pgrp is not None:
            pgrp.delete()
            Cluster.log_info("Deleted placement group %s", gname)
        else:
            Cluster.log_info("Placement group %s does not exist", gname)

    @staticmethod
    def get_launch_config(lconfig_name):
        auto_scale_conn = CloudHost.connect_autoscale()
        configs = auto_scale_conn.get_all_launch_configurations(names=[lconfig_name])
        if len(configs) > 0:
            return configs[0]
        return None

    @staticmethod
    def create_launch_config(lconfig_name, image_id, inst_type, key_name, security_groups,
                             spot_price=0,
                             user_data_file=None,
                             block_dev_mappings=None,
                             ebs_optimized=False,
                             overwrite=False):

        existing_config = Cluster.get_launch_config(lconfig_name)
        if existing_config is not None:
            if overwrite:
                existing_config.delete()
                Cluster.log_info("Deleted launch config %s to overwrite new config", lconfig_name)
            else:
                Cluster.log_error("Launch config %s already exists.", lconfig_name)
                raise Exception("Launch configuration already exists")

        auto_scale_conn = CloudHost.connect_autoscale()

        if user_data_file is None:
            user_data = None
        else:
            with open(user_data_file, 'r') as udf:
                user_data = udf.read()

        lconfig = LaunchConfiguration()
        lconfig.instance_type = inst_type
        lconfig.name = lconfig_name
        lconfig.image_id = image_id
        lconfig.key_name = key_name
        lconfig.security_groups = security_groups
        lconfig.user_data = user_data

        if spot_price > 0:
            lconfig.spot_price = spot_price

        if block_dev_mappings is not None:
            lconfig.block_device_mappings = block_dev_mappings

        if ebs_optimized:
            lconfig.ebs_optimized = True

        auto_scale_conn.create_launch_configuration(lconfig)
        Cluster.log_info("Created launch configuration %s with user data file %s", lconfig.name, user_data_file)

    @staticmethod
    def delete_launch_config(lconfig_name):
        existing_config = Cluster.get_launch_config(lconfig_name)
        if existing_config is not None:
            existing_config.delete()
            Cluster.log_info("Deleted launch config %s", lconfig_name)
        else:
            Cluster.log_info("Launch config %s does not exist", lconfig_name)

    @staticmethod
    def create_autoscale_group(gname, lconfig_name, placement_group, size, zones=None):
        existing_group = CloudHost.get_autoscale_group(gname)
        if existing_group is not None:
            Cluster.log_error("Autoscale group %s already exists!", gname)
            return None

        tags = [Tag(key='Name', value=gname, propagate_at_launch=True, resource_id=gname)]

        if zones is None:
            zones = [x.name for x in CloudHost.connect_ec2().get_all_zones()]

        Cluster.log_info("zones: %r", zones)
        ag = AutoScalingGroup(group_name=gname, availability_zones=zones,
                              launch_config=lconfig_name,
                              placement_group=placement_group,
                              tags=tags,
                              desired_capacity=0, min_size=0, max_size=size)
        conn = CloudHost.connect_autoscale()
        return conn.create_auto_scaling_group(ag)

    @staticmethod
    def delete_autoscale_group(gname, force=False):
        existing_group = CloudHost.get_autoscale_group(gname)
        if existing_group is not None:
            existing_group.delete(force_delete=force)
            Cluster.log_error("Autoscale group %s deleted (forced=%r)", gname, force)
        else:
            Cluster.log_info("Autoscale group %s does not exist", gname)
        return None

    # @staticmethod
    # def launch_into_placement_group(gname, ami_name, key, inst_type, num_inst, sec_grp, spot_price=None):
    #     conn = CloudHost.connect_ec2()
    #
    #     ami = CloudHost.get_image(ami_name)
    #     if ami is None:
    #         CloudHost.log_error("Image with name %s not found.", ami_name)
    #         return None
    #
    #     ami_id = ami.id
    #
    #     if spot_price is None:
    #         resev = conn.run_instances(ami_id, min_count=num_inst, max_count=num_inst,
    #                                    key_name=key, instance_type=inst_type, security_groups=[sec_grp],
    #                                    placement=CloudHost.REGION, placement_group=gname)
    #     else:
    #         resev = conn.request_spot_instances(spot_price, ami_id, count=num_inst,
    #                                             launch_group=gname,
    #                                             key_name=key, instance_type=inst_type, security_groups=[sec_grp],
    #                                             placement=CloudHost.REGION, placement_group=gname)
    #     return resev.id
    #
    # # @staticmethod
    # # def get_spot_request(gname):
    # #     conn = CloudHost.connect_ec2()
    # #     conn.get_all_spot_instance_requests()
    #
    # @staticmethod
    # def wait_for_placement_group(gname, num_inst):
    #     if Cluster.get_placement_group(gname) is None:
    #         return False, -1
    #     count = len(CloudHost.get_public_addresses_by_placement_group(gname))
    #     return (num_inst == count), count
