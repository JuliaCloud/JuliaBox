__author__ = 'tan'
from juliabox.jbox_tasks import JBoxHousekeepingPlugin
from juliabox.jbox_container import JBoxContainer
from juliabox.cloud.aws import CloudHost

from user_cluster import UserCluster

class ParallelHousekeep(JBoxHousekeepingPlugin):
    provides = [JBoxHousekeepingPlugin.PLUGIN_CLUSTER_HOUSEKEEPING]

    @staticmethod
    def terminate_or_delete_cluster(cluster_id):
        uc = UserCluster(None, gname=cluster_id)
        uc.terminate_or_delete()

    @staticmethod
    def do_housekeeping(_name, _mode):
        active_clusters = UserCluster.list_all_groupids()
        ParallelHousekeep.log_info("%d active clusters", len(active_clusters))
        if len(active_clusters) == 0:
            return
        active_sessions = JBoxContainer.get_active_sessions()
        for cluster_id in active_clusters:
            sess_id = "/" + UserCluster.sessname_for_cluster(cluster_id)
            if sess_id not in active_sessions:
                CloudHost.log_info("Session (%s) corresponding to cluster (%s) not found. Terminating cluster.",
                                   sess_id, cluster_id)
                ParallelHousekeep.terminate_or_delete_cluster(cluster_id)