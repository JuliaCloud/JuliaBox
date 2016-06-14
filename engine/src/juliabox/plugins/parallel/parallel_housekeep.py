__author__ = 'tan'
from juliabox.jbox_tasks import JBPluginTask
from juliabox.interactive import SessContainer
from juliabox.srvr_jboxd import jboxd_method
from juliabox.db import JBoxSessionProps, JBoxDBItemNotFound

from user_cluster import UserCluster


class ParallelHousekeep(JBPluginTask):
    provides = [JBPluginTask.JBP_CLUSTER]

    @staticmethod
    def terminate_or_delete_cluster(cluster_id):
        uc = UserCluster(None, gname=cluster_id)
        uc.terminate_or_delete()

    @staticmethod
    @jboxd_method
    def do_periodic_task(_mode):
        active_clusters = UserCluster.list_all_groupids()
        ParallelHousekeep.log_info("%d active clusters", len(active_clusters))
        if len(active_clusters) == 0:
            return
        for cluster_id in active_clusters:
            sessname = UserCluster.sessname_for_cluster(cluster_id)
            try:
                sess_props = JBoxSessionProps(sessname)
                if not sess_props.get_instance_id():
                    ParallelHousekeep.log_info(
                        "Session (%s) corresponding to cluster (%s) not found. Terminating cluster.",
                        sessname, cluster_id)
                    ParallelHousekeep.terminate_or_delete_cluster(cluster_id)
            except JBoxDBItemNotFound:
                pass