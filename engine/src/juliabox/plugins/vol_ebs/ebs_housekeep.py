__author__ = 'tan'
import pytz
import os
import datetime

from juliabox.jbox_tasks import JBPluginTask
from juliabox.db import JBoxSessionProps
from juliabox.plugins.compute_ec2 import EBSVol
from juliabox.jbox_util import unique_sessname
from juliabox.srvr_jboxd import jboxd_method
from juliabox.interactive import SessContainer
from disk_state_tbl import JBoxDiskState
from ebs import JBoxEBSVol


class JBoxEBSHousekeep(JBPluginTask):
    provides = [JBPluginTask.JBP_CLUSTER, JBPluginTask.JBP_NODE]

    @staticmethod
    @jboxd_method
    def do_periodic_task(mode):
        if mode == JBPluginTask.JBP_CLUSTER:
            JBoxEBSHousekeep.do_cluster_housekeeping()
        elif mode == JBPluginTask.JBP_NODE:
            JBoxEBSHousekeep.do_node_housekeeping()

    @staticmethod
    def do_node_housekeeping():
        JBoxEBSHousekeep.log_debug("starting node housekeeping")
        for device, vol in JBoxEBSVol.get_mapped_volumes().iteritems():
            deviceid = os.path.basename(device)
            vol_id = vol.volume_id
            vol = EBSVol.get_volume(vol_id)
            user_id = vol.tags['Name'] if 'Name' in vol.tags else None
            if user_id is None:
                continue
            sessname = unique_sessname(user_id)
            cont = SessContainer.get_by_name(sessname)
            if cont is not None:
                continue
            JBoxEBSHousekeep.log_debug("Found orphaned volume %s for %s, %s", vol_id, user_id, sessname)
            ebsvol = JBoxEBSVol(deviceid, sessname=sessname)
            ebsvol.release(backup=True)
        JBoxEBSHousekeep.log_debug("finished node housekeeping")

    @staticmethod
    def do_cluster_housekeeping():
        JBoxEBSHousekeep.log_debug("starting cluster housekeeping")
        detached_disks = JBoxDiskState.get_detached_disks()
        time_now = datetime.datetime.now(pytz.utc)
        for disk_key in detached_disks:
            disk_info = JBoxDiskState(disk_key=disk_key)
            user_id = disk_info.get_user_id()
            sess_props = JBoxSessionProps(unique_sessname(user_id))
            incomplete_snapshots = []
            modified = False
            for snap_id in disk_info.get_snapshot_ids():
                if not EBSVol.is_snapshot_complete(snap_id):
                    incomplete_snapshots.append(snap_id)
                    continue
                JBoxEBSHousekeep.log_debug("updating latest snapshot of user %s to %s", user_id, snap_id)
                old_snap_id = sess_props.get_snapshot_id()
                sess_props.set_snapshot_id(snap_id)
                modified = True
                if old_snap_id is not None:
                    EBSVol.delete_snapshot(old_snap_id)
            if modified:
                sess_props.save()
                disk_info.set_snapshot_ids(incomplete_snapshots)
                disk_info.save()
            if len(incomplete_snapshots) == 0:
                if (time_now - disk_info.get_detach_time()).total_seconds() > 24*60*60:
                    vol_id = disk_info.get_volume_id()
                    JBoxEBSHousekeep.log_debug("volume %s for user %s unused for too long", vol_id, user_id)
                    disk_info.delete()
                    EBSVol.detach_volume(vol_id, delete=True)
            else:
                JBoxEBSHousekeep.log_debug("ongoing snapshots of user %s: %r", user_id, incomplete_snapshots)
        JBoxEBSHousekeep.log_debug("finished cluster housekeeping")
