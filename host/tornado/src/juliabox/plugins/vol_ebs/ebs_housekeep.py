__author__ = 'tan'
import pytz
import datetime

from juliabox.jbox_tasks import JBoxHousekeepingPlugin
from juliabox.db import JBoxSessionProps
from juliabox.cloud.aws import CloudHost
from juliabox.jbox_util import unique_sessname

from disk_state_tbl import JBoxDiskState

class JBoxEBSHousekeep(JBoxHousekeepingPlugin):
    provides = [JBoxHousekeepingPlugin.PLUGIN_CLUSTER_HOUSEKEEPING]

    @staticmethod
    def do_housekeeping(_name, _mode):
        detached_disks = JBoxDiskState.get_detached_disks()
        time_now = datetime.datetime.now(pytz.utc)
        for disk_key in detached_disks:
            disk_info = JBoxDiskState(disk_key=disk_key)
            user_id = disk_info.get_user_id()
            sess_props = JBoxSessionProps(unique_sessname(user_id))
            incomplete_snapshots = []
            modified = False
            for snap_id in disk_info.get_snapshot_ids():
                if not CloudHost.is_snapshot_complete(snap_id):
                    incomplete_snapshots.append(snap_id)
                    continue
                JBoxEBSHousekeep.log_debug("updating latest snapshot of user %s to %s", user_id, snap_id)
                old_snap_id = sess_props.get_snapshot_id()
                sess_props.set_snapshot_id(snap_id)
                modified = True
                if old_snap_id is not None:
                    CloudHost.delete_snapshot(old_snap_id)
            if modified:
                sess_props.save()
                disk_info.set_snapshot_ids(incomplete_snapshots)
                disk_info.save()
            if len(incomplete_snapshots) == 0:
                if (time_now - disk_info.get_detach_time()).total_seconds() > 24*60*60:
                    vol_id = disk_info.get_volume_id()
                    JBoxEBSHousekeep.log_debug("volume %s for user %s unused for too long", vol_id, user_id)
                    disk_info.delete()
                    CloudHost.detach_volume(vol_id, delete=True)
            else:
                JBoxEBSHousekeep.log_debug("ongoing snapshots of user %s: %r", user_id, incomplete_snapshots)
