from db.db_base import JBoxDB
from db.user_v2 import JBoxUserV2
from db.invites import JBoxInvite
from db.accounting_v2 import JBoxAccountingV2
from db.container import JBoxSessionProps
from db.dynconfig import JBoxDynConfig
from cloud.aws import CloudHost


def configure_db(cfg):
    JBoxDB.configure(cfg)
    cloud_cfg = cfg['cloud_host']

    if 'jbox_users_v2' in cloud_cfg:
        JBoxUserV2.NAME = cloud_cfg['jbox_users_v2']
    if 'jbox_invites' in cloud_cfg:
        JBoxInvite.NAME = cloud_cfg['jbox_invites']
    if 'jbox_accounting_v2' in cloud_cfg:
        JBoxAccountingV2.NAME = cloud_cfg['jbox_accounting_v2']
    if 'jbox_session' in cloud_cfg:
        JBoxSessionProps.NAME = cloud_cfg['jbox_session']
    if 'jbox_dynconfig' in cloud_cfg:
        JBoxDynConfig.NAME = cloud_cfg['jbox_dynconfig']


def is_cluster_leader():
    if not CloudHost.ENABLED['cloudwatch']:
        return False

    cluster = CloudHost.INSTALL_ID
    instances = CloudHost.get_autoscaled_instances()
    leader = JBoxDynConfig.get_cluster_leader(cluster)
    JBoxDB.log_debug("cluster: %s. instances: %s. leader: %s", cluster, repr(instances), repr(leader))

    # if none set, or set instance is dead elect self as leader, but wait till next cycle to prevent conflicts
    if (leader is None) or (leader not in instances):
        JBoxDB.log_info("setting self (%s) as cluster leader", CloudHost.instance_id())
        JBoxDynConfig.set_cluster_leader(cluster, CloudHost.instance_id())
        return False
    return leader == CloudHost.instance_id()


def publish_stats():
    JBoxUserV2.calc_stats()
    JBoxUserV2.log_debug("stats: %r", JBoxUserV2.STATS)
    JBoxDynConfig.set_stat(CloudHost.INSTALL_ID, "stat_users", JBoxUserV2.STATS)
