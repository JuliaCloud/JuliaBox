import datetime
import pytz

from cloud import Compute
from jbox_tasks import JBoxAsyncJob
from jbox_util import JBoxCfg
from jbox_container_base import JBoxContainerBase
from vol import VolMgr, JBoxVol
import docker.utils


class JBoxContainer(JBoxContainerBase):
    CONTAINER_PORT_BINDINGS = {4200: ('127.0.0.1',), 8000: ('127.0.0.1',), 8998: ('127.0.0.1',)}
    PINGS = {}
    DCKR_IMAGE = None
    MEM_LIMIT = None

    # By default all groups have 1024 shares.
    # A group with 100 shares will get a ~10% portion of the CPU time (https://wiki.archlinux.org/index.php/Cgroups)
    CPU_LIMIT = 1024
    PORTS = [4200, 8000, 8998]
    VOLUMES = ['/home/juser', JBoxVol.PKG_MOUNT_POINT]
    MAX_CONTAINERS = 0
    VALID_CONTAINERS = {}
    INITIAL_DISK_USED_PCT = None
    LAST_CPU_PCT = None

    def get_host_ports(self):
        return self._get_host_ports(JBoxContainer.PORTS)

    def get_disk_allocated(self):
        disk = VolMgr.get_disk_from_container(self.dockid, JBoxVol.JBP_USERHOME)
        if disk is not None:
            return disk.get_disk_allocated_size()
        return 0

    @staticmethod
    def configure():
        JBoxContainerBase.DCKR = JBoxCfg.dckr
        JBoxContainer.DCKR_IMAGE = JBoxCfg.get('interactive.docker_image')
        JBoxContainer.MEM_LIMIT = JBoxCfg.get('interactive.mem_limit')
        JBoxContainer.CPU_LIMIT = JBoxCfg.get('interactive.cpu_limit')
        JBoxContainer.MAX_CONTAINERS = JBoxCfg.get('interactive.numlocalmax')

    @staticmethod
    def _create_new(name, email):
        home_disk = VolMgr.get_disk_for_user(email)
        pkgs_disk = VolMgr.get_pkg_mount_for_user(email)

        vols = {
            home_disk.disk_path: {
                'bind': JBoxContainer.VOLUMES[0],
                'ro': False
            },
            pkgs_disk.disk_path: {
                'bind': JBoxContainer.VOLUMES[1],
                'ro': True
            }
        }

        hostcfg = docker.utils.create_host_config(binds=vols,
                                                  port_bindings=JBoxContainer.CONTAINER_PORT_BINDINGS,
                                                  mem_limit=JBoxContainer.MEM_LIMIT)
        jsonobj = JBoxContainerBase.DCKR.create_container(JBoxContainer.DCKR_IMAGE,
                                                          detach=True,
                                                          host_config=hostcfg,
                                                          cpu_shares=JBoxContainer.CPU_LIMIT,
                                                          ports=JBoxContainer.PORTS,
                                                          volumes=JBoxContainer.VOLUMES,
                                                          hostname='juliabox',
                                                          name=name)
        dockid = jsonobj["Id"]
        cont = JBoxContainer(dockid)
        JBoxContainer.log_info("Created %s with hostcfg %r, cpu_limit: %r, volumes: %r", cont.debug_str(), hostcfg,
                               JBoxContainer.CPU_LIMIT, vols)
        return cont

    @staticmethod
    def invalidate_container(cname):
        if not cname.startswith("/"):
            cname = "/" + cname
        if JBoxContainer.VALID_CONTAINERS.has_key(cname):
            JBoxContainer.log_info("Invalidating container %s", cname)
            del JBoxContainer.VALID_CONTAINERS[cname]

    @staticmethod
    def launch_by_name(name, email, reuse=True):
        JBoxContainer.log_info("Launching container %s", name)

        cont = JBoxContainer.get_by_name(name)

        if (cont is not None) and not reuse:
            cont.delete()
            cont = None

        if cont is None:
            cont = JBoxContainer._create_new(name, email)

        try:
            if not (cont.is_running() or cont.is_restarting()):
                cont.start()
            #else:
            #    cont.restart()
        except:
            cont.delete()
            raise

        return cont

    @staticmethod
    def maintain(max_timeout=0, inactive_timeout=0):
        JBoxContainer.log_info("Starting container maintenance...")
        tnow = datetime.datetime.now(pytz.utc)
        tmin = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=pytz.utc)

        stop_before = (tnow - datetime.timedelta(seconds=max_timeout)) if (max_timeout > 0) else tmin
        stop_inacive_before = (tnow - datetime.timedelta(seconds=inactive_timeout)) if (inactive_timeout > 0) else tmin

        all_containers = JBoxContainerBase.session_containers(allcontainers=True)
        all_cnames = {}
        container_id_list = []
        for cdesc in all_containers:
            cid = cdesc['Id']
            cont = JBoxContainer(cid)
            container_id_list.append(cid)
            cname = cont.get_name()

            if cname is None:
                JBoxContainer.log_debug("Ignoring %s", cont.debug_str())
                continue

            all_cnames[cname] = cid

            c_is_active = cont.is_running() or cont.is_restarting()
            last_ping = JBoxContainer._get_last_ping(cname)

            # if we don't have a ping record, create one (we must have restarted) 
            if (last_ping is None) and c_is_active:
                JBoxContainer.log_info("Discovered new container %s", cont.debug_str())
                JBoxContainer.record_ping(cname)

            start_time = cont.time_started()
            # check that start time is not absurdly small (indicates a continer that's starting up)
            start_time_not_zero = (tnow-start_time).total_seconds() < (365*24*60*60)
            if (start_time < stop_before) and start_time_not_zero:
                # don't allow running beyond the limit for long running sessions
                # JBoxContainer.log_info("time_started " + str(cont.time_started()) +
                #               " delete_before: " + str(delete_before) +
                #               " cond: " + str(cont.time_started() < delete_before))
                JBoxContainer.log_warn("Running beyond allowed time %s. Scheduling cleanup.", cont.debug_str())
                JBoxContainer.invalidate_container(cont.get_name())
                JBoxAsyncJob.async_backup_and_cleanup(cont.dockid)
            elif (last_ping is not None) and c_is_active and (last_ping < stop_inacive_before):
                # if inactive for too long, stop it
                # JBoxContainer.log_info("last_ping " + str(last_ping) + " stop_before: " + str(stop_before) +
                #           " cond: " + str(last_ping < stop_before))
                JBoxContainer.log_warn("Inactive beyond allowed time %s. Scheduling cleanup.", cont.debug_str())
                JBoxContainer.invalidate_container(cont.get_name())
                JBoxAsyncJob.async_backup_and_cleanup(cont.dockid)

        # delete ping entries for non exixtent containers
        for cname in JBoxContainer.PINGS.keys():
            if cname not in all_cnames:
                del JBoxContainer.PINGS[cname]

        JBoxContainer.VALID_CONTAINERS = all_cnames
        VolMgr.refresh_disk_use_status(container_id_list=container_id_list)
        JBoxContainer.log_info("Finished container maintenance.")

    @staticmethod
    def is_valid_container(cname, hostports):
        cont = None
        if cname in JBoxContainer.VALID_CONTAINERS:
            try:
                cont = JBoxContainer(JBoxContainer.VALID_CONTAINERS[cname])
            except:
                pass
        else:
            all_containers = JBoxContainer.session_containers(allcontainers=True)
            for cdesc in all_containers:
                cid = cdesc['Id']
                cont = JBoxContainer(cid)
                cont_name = cont.get_name()
                JBoxContainer.VALID_CONTAINERS[cont_name] = cid
                if cname == cont_name:
                    break

        if cont is None:
            return False

        try:
            return hostports == cont.get_host_ports()
        except:
            return False

    @staticmethod
    def get_active_sessions():
        instances = Compute.get_all_instances()

        active_sessions = set()
        for inst in instances:
            sessions = JBoxAsyncJob.sync_session_status(inst)['data']
            if len(sessions) > 0:
                for sess_id in sessions.keys():
                    active_sessions.add(sess_id)

        return active_sessions

    def backup_and_cleanup(self):
        self.stop()
        self.delete(backup=True)

    # def backup(self):
    #     JBoxContainer.log_info("Backing up %s", self.debug_str())
    #     disk = VolMgr.get_disk_from_container(self.dockid)
    #     if disk is not None:
    #         disk.backup()

    @staticmethod
    def get_by_name(name):
        if not name.startswith("/"):
            nname = "/" + unicode(name)
        else:
            nname = unicode(name)

        for c in JBoxContainer.session_containers(allcontainers=True):
            if ('Names' in c) and (c['Names'] is not None) and (c['Names'][0] == nname):
                return JBoxContainer(c['Id'])
        return None

    @staticmethod
    def record_ping(name):
        JBoxContainer.PINGS[name] = datetime.datetime.now(pytz.utc)
        # log_info("Recorded ping for %s", name)

    @staticmethod
    def _get_last_ping(name):
        return JBoxContainer.PINGS[name] if (name in JBoxContainer.PINGS) else None

    def on_stop(self):
        self.record_usage()

    def on_start(self):
        cname = self.get_name()
        if cname is not None:
            JBoxContainer.record_ping(cname)

    def on_restart(self):
        self.on_start()

    def on_kill(self):
        self.on_stop()

    def before_delete(self, cname, backup):
        for disktype in (JBoxVol.JBP_USERHOME, JBoxVol.JBP_PKGBUNDLE, JBoxVol.JBP_DATA):
            disk = VolMgr.get_disk_from_container(self.dockid, disktype)
            if disk is not None:
                disk.release(backup=backup)
        if cname is not None:
            JBoxContainer.PINGS.pop(cname, None)
