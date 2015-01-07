from db.db_base import JBoxDB
from db.user_v2 import JBoxUserV2
from db.invites import JBoxInvite
from db.accounting_v2 import JBoxAccountingV2
from db.container import JBoxSessionProps
from db.dynconfig import JBoxDynConfig
from db.disk_state import JBoxDiskState
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
    if 'jbox_diskstate' in cloud_cfg:
        JBoxDiskState.NAME = cloud_cfg['jbox_diskstate']


def is_proposed_cluster_leader():
    if not CloudHost.ENABLED['cloudwatch']:
        return False

    cluster = CloudHost.INSTALL_ID
    leader = JBoxDynConfig.get_cluster_leader(cluster)
    return leader == CloudHost.instance_id()


def is_cluster_leader():
    if not CloudHost.ENABLED['cloudwatch']:
        return False

    cluster = CloudHost.INSTALL_ID
    instances = CloudHost.get_autoscaled_instances()
    leader = JBoxDynConfig.get_cluster_leader(cluster)
    ami_recentness = CloudHost.get_ami_recentness()
    JBoxDB.log_debug("cluster: %s. instances: %s. leader: %s. ami_recentness: %d",
                     cluster, repr(instances), repr(leader), ami_recentness)

    # if none set, or set instance is dead elect self as leader, but wait till next cycle to prevent conflicts
    if (leader is None) or (leader not in instances) and (ami_recentness >= 0):
        JBoxDB.log_info("setting self (%s) as cluster leader", CloudHost.instance_id())
        JBoxDynConfig.set_cluster_leader(cluster, CloudHost.instance_id())
        return False

    is_leader = (leader == CloudHost.instance_id())

    # if running an older ami, step down from cluster leader
    if (ami_recentness < 0) and is_leader:
        JBoxDB.log_info("unmarking self (%s) as cluster leader", CloudHost.instance_id())
        JBoxDynConfig.unset_cluster_leader(cluster)
        return False

    return is_leader


def publish_stats():
    JBoxUserV2.calc_stats()
    JBoxUserV2.log_debug("stats: %r", JBoxUserV2.STATS)
    JBoxDynConfig.set_stat(CloudHost.INSTALL_ID, JBoxUserV2.STAT_NAME, JBoxUserV2.STATS)
