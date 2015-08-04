__author__ = 'tan'

import boto
import boto.route53

from juliabox.cloud import JBoxCloudPlugin
from juliabox.jbox_util import JBoxCfg


class JBoxRoute53(JBoxCloudPlugin):
    provides = [JBoxCloudPlugin.PLUGIN_DNS, JBoxCloudPlugin.PLUGIN_DNS_ROUTE53]

    DOMAIN = None
    REGION = None
    CONN = None
    BUCKETS = dict()

    @staticmethod
    def configure():
        cloud_host = JBoxCfg.get("cloud_host")
        JBoxRoute53.DOMAIN = cloud_host['domain']
        JBoxRoute53.REGION = cloud_host["region"]

    @staticmethod
    def domain():
        if JBoxRoute53.DOMAIN is None:
            JBoxRoute53.configure()
        return JBoxRoute53.DOMAIN

    @staticmethod
    def connect():
        if JBoxRoute53.CONN is None:
            JBoxRoute53.configure()
            JBoxRoute53.CONN = boto.route53.connect_to_region(JBoxRoute53.REGION)
        return JBoxRoute53.CONN

    @staticmethod
    def add_cname(name, value):
        zone = JBoxRoute53.connect().get_zone(JBoxRoute53.DOMAIN)
        zone.add_cname(name, value)

    @staticmethod
    def delete_cname(name):
        zone = JBoxRoute53.connect().get_zone(JBoxRoute53.DOMAIN)
        try:
            zone.delete_cname(name)
            JBoxRoute53.log_warn("Prior dns registration was found for %s", name)
        except:
            JBoxRoute53.log_debug("No prior dns registration found for %s", name)
