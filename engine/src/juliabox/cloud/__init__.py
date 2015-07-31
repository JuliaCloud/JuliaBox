__author__ = 'tan'

from juliabox.jbox_util import LoggerMixin, JBoxPluginType


class JBoxCloudPlugin(LoggerMixin):
    """ The base class for cloud service providers.

    It is a plugin mount point, looking for features:
    - cloud.bucketstore (e.g. s3, swift)
    - cloud.dns (e.g. route53)
    """

    PLUGIN_BUCKETSTORE = "cloud.bucketstore"
    PLUGIN_BUCKETSTORE_S3 = "cloud.bucketstore.s3"

    PLUGIN_DNS = "cloud.dns"
    PLUGIN_DNS_ROUTE53 = "cloud.dns.route53"

    __metaclass__ = JBoxPluginType