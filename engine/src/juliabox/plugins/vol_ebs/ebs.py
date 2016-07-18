import os
import threading
import time
from string import ascii_lowercase

from juliabox.plugins.compute_ec2 import EBSVol, CompEC2
from juliabox.db import JBoxSessionProps
from juliabox.jbox_util import unique_sessname, JBoxCfg
from juliabox.vol import JBoxVol
from juliabox.cloud import Compute
from disk_state_tbl import JBoxDiskState


class JBoxEBSVol(JBoxVol):
    provides = [JBoxVol.JBP_DATA_EBS, JBoxVol.JBP_DATA]

    DEVICES = []
    MAX_DISKS = 0
    DISK_LIMIT = None
    DISK_USE_STATUS = {}
    DISK_RESERVE_TIME = {}
    DISK_TEMPLATE_SNAPSHOT = None
    LOCK = None

    @staticmethod
    def configure():
        num_disks_max = JBoxCfg.get('numdisksmax')
        JBoxEBSVol.DISK_LIMIT = 10
        JBoxEBSVol.MAX_DISKS = num_disks_max
        JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT = JBoxCfg.get('cloud_host.ebs_template')

        JBoxEBSVol.DEVICES = JBoxEBSVol._guess_configured_devices('xvd', num_disks_max)
        JBoxEBSVol.log_debug("Assuming %d EBS volumes configured in range xvdba..xvdcz", len(JBoxEBSVol.DEVICES))

        JBoxEBSVol.LOCK = threading.Lock()
        JBoxEBSVol.refresh_disk_use_status()

    @classmethod
    def get_disk_allocated_size(cls):
        return JBoxEBSVol.DISK_LIMIT * 1000000000

    @staticmethod
    def _guess_configured_devices(devidpfx, num_disks):
        devices = []
        for pfx1 in 'bc':
            for pfx2 in ascii_lowercase:
                devices.append(devidpfx+pfx1+pfx2)
                if len(devices) == num_disks:
                    return devices
        return devices

    @staticmethod
    def refresh_disk_use_status(container_id_list=None):
        JBoxEBSVol.log_debug("Refrshing EBS disk use status")
        JBoxEBSVol.LOCK.acquire()
        try:
            nfree = 0
            for idx in range(0, JBoxEBSVol.MAX_DISKS):
                dev = JBoxEBSVol.DEVICES[idx]
                if JBoxEBSVol._is_reserved(dev):
                    JBoxEBSVol.DISK_USE_STATUS[dev] = True
                else:
                    JBoxEBSVol.DISK_USE_STATUS[dev] = False
                    nfree += 1

            for device, volume in JBoxEBSVol.get_mapped_volumes().iteritems():
                JBoxEBSVol.DISK_USE_STATUS[os.path.basename(device)] = True
                nfree -= 1
            JBoxEBSVol.log_info("EBS Disk free: " + str(nfree) + "/" + str(JBoxEBSVol.MAX_DISKS))
        except:
            JBoxEBSVol.log_exception("Exception refrshing EBS disk use status")
        finally:
            JBoxEBSVol.LOCK.release()

    @staticmethod
    def get_mapped_volumes():
        allmaps = EBSVol.get_mapped_volumes()
        JBoxEBSVol.log_debug("Devices mapped: %r", allmaps)
        return dict((d, v) for d, v in allmaps.iteritems() if os.path.basename(d) in JBoxEBSVol.DEVICES)

    @staticmethod
    def _get_unused_disk_id():
        for idx in range(0, JBoxEBSVol.MAX_DISKS):
            dev = JBoxEBSVol.DEVICES[idx]
            if not JBoxEBSVol.DISK_USE_STATUS[dev]:
                return dev
        return None

    @staticmethod
    def _is_reserved(idx):
        if (idx in JBoxEBSVol.DISK_RESERVE_TIME) and (JBoxEBSVol.DISK_RESERVE_TIME[idx] < time.time()):
            del JBoxEBSVol.DISK_RESERVE_TIME[idx]
        return idx in JBoxEBSVol.DISK_RESERVE_TIME

    @staticmethod
    def _mark_disk_used(idx, used=True, for_secs=0):
        JBoxEBSVol.DISK_USE_STATUS[idx] = used
        if used and (for_secs > 0):
            JBoxEBSVol.DISK_RESERVE_TIME[idx] = time.time() + for_secs
        else:
            if idx in JBoxEBSVol.DISK_RESERVE_TIME:
                del JBoxEBSVol.DISK_RESERVE_TIME[idx]

    @staticmethod
    def _reserve_disk_id():
        JBoxEBSVol.LOCK.acquire()
        try:
            disk_id = JBoxEBSVol._get_unused_disk_id()
            JBoxEBSVol._mark_disk_used(disk_id, for_secs=120)
            return disk_id
        finally:
            JBoxEBSVol.LOCK.release()

    @staticmethod
    def is_mount_path(fs_path):
        # EBS volumes are not mounted on host
        return False

    @staticmethod
    def disk_ids_used_pct():
        pct = (sum(JBoxEBSVol.DISK_USE_STATUS.values()) * 100) / len(JBoxEBSVol.DISK_USE_STATUS)
        return min(100, max(0, pct))

    @staticmethod
    def get_disk_for_user(user_email):
        JBoxEBSVol.log_debug("creating EBS volume for %s", user_email)

        disk_id = JBoxEBSVol._reserve_disk_id()
        if disk_id is None:
            raise Exception("No free disk available")

        try:
            existing_disk = JBoxDiskState(cluster_id=CompEC2.INSTALL_ID, region_id=CompEC2.REGION,
                                          user_id=user_email)
        except Exception as ex:
            JBoxEBSVol.log_debug("No existing disk for %s. Exception %r", user_email, ex)
            existing_disk = None

        if existing_disk is None:
            sess_id = unique_sessname(user_email)
            sess_props = JBoxSessionProps(Compute.get_install_id(), sess_id, create=True, user_id=user_email)
            if sess_props.is_new:
                sess_props.save()
            snap_id = sess_props.get_snapshot_id()
            if snap_id is None:
                snap_id = JBoxEBSVol.DISK_TEMPLATE_SNAPSHOT

            JBoxEBSVol.log_debug("will use snapshot id %s for %s", snap_id, user_email)

            dev_path, vol_id = EBSVol.create_new_volume(snap_id, disk_id, tag=user_email,
                                                        disk_sz_gb=JBoxEBSVol.DISK_LIMIT)
            existing_disk = JBoxDiskState(cluster_id=CompEC2.INSTALL_ID, region_id=CompEC2.REGION,
                                          user_id=user_email,
                                          volume_id=vol_id,
                                          attach_time=None,
                                          create=True)
        else:
            dev_path = EBSVol.attach_volume(existing_disk.get_volume_id(), disk_id)

        existing_disk.set_state(JBoxDiskState.STATE_ATTACHING)
        existing_disk.save()

        return JBoxEBSVol(dev_path, user_email=user_email)

    @staticmethod
    def get_disk_from_container(cid):
        container_name = JBoxVol.get_cname(cid)
        sessname = container_name[1:]
        for dev, vol in JBoxEBSVol.get_mapped_volumes().iteritems():
            vol = EBSVol.get_volume(vol.volume_id)
            if 'Name' in vol.tags:
                name = vol.tags['Name']
                if unique_sessname(name) == sessname:
                    return JBoxEBSVol(dev, sessname=sessname)
        return None

    def _backup(self, clear_volume=False):
        sess_props = JBoxSessionProps(Compute.get_install_id(), self.sessname)
        desc = sess_props.get_user_id() + " JuliaBox Backup"
        disk_id = self.disk_path.split('/')[-1]
        snap_id = EBSVol.snapshot_volume(dev_id=disk_id, tag=self.sessname, description=desc, wait_till_complete=False)
        return snap_id

    def release(self, backup=False):
        sess_props = JBoxSessionProps(Compute.get_install_id(), self.sessname)
        existing_disk = JBoxDiskState(cluster_id=CompEC2.INSTALL_ID, region_id=CompEC2.REGION,
                                      user_id=sess_props.get_user_id())
        existing_disk.set_state(JBoxDiskState.STATE_DETACHING)
        existing_disk.save()

        disk_id = self.disk_path.split('/')[-1]
        if backup:
            snap_id = self._backup()
        else:
            snap_id = None
        vol_id = EBSVol.get_volume_id_from_device(disk_id)
        EBSVol.detach_volume(vol_id, delete=False)

        if snap_id is not None:
            existing_disk.add_snapshot_id(snap_id)

        existing_disk.set_state(JBoxDiskState.STATE_DETACHED)
        existing_disk.save()
