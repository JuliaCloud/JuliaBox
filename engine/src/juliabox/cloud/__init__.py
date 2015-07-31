__author__ = 'tan'

from juliabox.jbox_util import LoggerMixin, JBoxPluginType


class JBoxCloudPlugin(LoggerMixin):
    """ The base class for cloud service providers.

    It is a plugin mount point, looking for features:
    - cloud.bucketstore (e.g. s3, swift)
    """

    PLUGIN_BUCKETSTORE = "cloud.bucketstore"
    PLUGIN_BUCKETSTORE_S3 = "cloud.bucketstore.s3"

    __metaclass__ = JBoxPluginType