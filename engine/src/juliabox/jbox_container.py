__author__ = 'tan'
import multiprocessing
import psutil

from jbox_util import LoggerMixin, parse_iso_time
from juliabox.db import JBPluginDB


class BaseContainer(LoggerMixin):
    DCKR = None
    LAST_CPU_PCT = None
    INITIAL_DISK_USED_PCT = None

    # JuliaBox service daemon container names are suffixed so that they are not treated as regular session containers.
    # Can move to an exclusion list if more complicated patterns are required.
    CONTAINER_NAME_SEP = '_'
    SFX_SVC = CONTAINER_NAME_SEP + 'jboxsvc'
    SFX_API = CONTAINER_NAME_SEP + 'jboxapi'
    SFX_INT = CONTAINER_NAME_SEP + 'jboxint'

    def __init__(self, dockid):
        self.dockid = dockid
        self.props = None
        self.dbgstr = None
        self.host_ports = None

    def refresh(self):
        self.props = None
        self.dbgstr = None
        self.host_ports = None

    def get_props(self):
        if self.props is None:
            self.props = BaseContainer.DCKR.inspect_container(self.dockid)
        return self.props

    def _get_host_ports(self, ports):
        props = self.get_props()
        cont_ports = props['NetworkSettings']['Ports']
        port_map = []
        for port in ports:
            tcp_port = str(port) + '/tcp'
            port_map.append(cont_ports[tcp_port][0]['HostPort'])
        return tuple(port_map)

    def get_cpu_allocated(self):
        props = self.get_props()
        cfg = props['HostConfig']
        cpu_shares = cfg.get('CpuShares', 1024)
        num_cpus = multiprocessing.cpu_count()
        return max(1, int(num_cpus * cpu_shares / 1024))

    def get_memory_allocated(self):
        props = self.get_props()
        cfg = props['HostConfig']
        mem = cfg.get('Memory', 0)
        if mem > 0:
            return mem
        return psutil.virtual_memory().total

    def debug_str(self):
        if self.dbgstr is None:
            self.dbgstr = self.__class__.__name__ + " id=" + str(self.dockid) + ", name=" + str(self.get_name())
        return self.dbgstr

    def get_name(self):
        try:
            props = self.get_props()
            return props['Name'] if ('Name' in props) else None
        except:
            # container was deleted
            return None

    def get_image_names(self):
        props = self.get_props()
        img_id = props['Image']
        for img in BaseContainer.DCKR.images():
            if img['Id'] == img_id:
                return img['RepoTags']
        return []

    @staticmethod
    def session_containers(allcontainers=True):
        sessions = []
        for c in BaseContainer.DCKR.containers(all=allcontainers):
            name = c["Names"][0] if (("Names" in c) and (c["Names"] is not None)) else c["Id"][0:12]
            if not name.endswith(BaseContainer.SFX_SVC) and not name.endswith(BaseContainer.SFX_API):
                sessions.append(c)
        return sessions

    @staticmethod
    def api_containers(allcontainers=True):
        return BaseContainer._containers_of_type(BaseContainer.SFX_API, allcontainers=allcontainers)

    @staticmethod
    def internal_containers(allcontainers=True):
        return BaseContainer._containers_of_type(BaseContainer.SFX_SVC, allcontainers=allcontainers)

    @staticmethod
    def num_active(sfx=None):
        cnt = 0
        for c in BaseContainer.DCKR.containers(all=True):
            name = c["Names"][0] if (("Names" in c) and (c["Names"] is not None)) else c["Id"][0:12]
            if name.endswith(BaseContainer.SFX_SVC):
                typ = BaseContainer.SFX_SVC
            elif name.endswith(BaseContainer.SFX_API):
                typ = BaseContainer.SFX_API
            else:
                typ = BaseContainer.SFX_INT

            if ((sfx is None) and (typ != BaseContainer.SFX_SVC)) or (typ == sfx):
                cnt += 1
        return cnt

    @staticmethod
    def _containers_of_type(sfx, allcontainers=True):
        sessions = []
        for c in BaseContainer.DCKR.containers(all=allcontainers):
            name = c["Names"][0] if (("Names" in c) and (c["Names"] is not None)) else c["Id"][0:12]
            if name.endswith(sfx):
                sessions.append(c)
        return sessions

    def is_running(self):
        props = self.get_props()
        state = props['State']
        return state['Running'] if 'Running' in state else False

    def is_restarting(self):
        props = self.get_props()
        state = props['State']
        return state['Restarting'] if 'Restarting' in state else False

    def time_started(self):
        props = self.get_props()
        return parse_iso_time(props['State']['StartedAt'])

    def time_finished(self):
        props = self.get_props()
        return parse_iso_time(props['State']['FinishedAt'])

    def time_created(self):
        props = self.get_props()
        return parse_iso_time(props['Created'])

    def on_stop(self):
        pass

    def on_start(self):
        pass

    def on_restart(self):
        pass

    def on_kill(self):
        pass

    def before_delete(self, cname, backup):
        pass

    def stop(self):
        BaseContainer.log_info("Stopping %s", self.debug_str())
        self.refresh()
        if not self.is_running():
            BaseContainer.log_info("Already stopped or restarting %s", self.debug_str())
            return
        BaseContainer.DCKR.stop(self.dockid, timeout=5)
        self.refresh()
        BaseContainer.log_info("Stopped %s", self.debug_str())
        self.on_stop()

    def start(self):
        self.refresh()
        BaseContainer.log_info("Starting %s", self.debug_str())
        if self.is_running() or self.is_restarting():
            BaseContainer.log_warn("Already started %s", self.debug_str())
            return
        BaseContainer.DCKR.start(self.dockid)
        self.refresh()
        BaseContainer.log_info("Started %s", self.debug_str())
        self.on_start()

    def restart(self):
        self.refresh()
        BaseContainer.log_info("Restarting %s", self.debug_str())
        BaseContainer.DCKR.restart(self.dockid, timeout=5)
        self.refresh()
        BaseContainer.log_info("Restarted %s", self.debug_str())
        self.on_restart()

    def kill(self):
        BaseContainer.log_info("Killing %s", self.debug_str())
        BaseContainer.DCKR.kill(self.dockid)
        self.refresh()
        BaseContainer.log_info("Killed %s", self.debug_str())
        self.on_kill()

    def delete(self, backup=False):
        BaseContainer.log_info("Deleting %s", self.debug_str())
        self.refresh()
        cname = self.get_name()
        if self.is_running() or self.is_restarting():
            self.kill()
        self.before_delete(cname, backup=backup)
        BaseContainer.DCKR.remove_container(self.dockid)
        BaseContainer.log_info("Deleted %s", self.debug_str())

    def record_usage(self):
        plugin = JBPluginDB.jbox_get_plugin(JBPluginDB.JBP_USAGE_ACCOUNTING)
        if plugin is not None:
            plugin.record_session_time(self.get_name(), self.get_image_names(), self.time_created(), self.time_finished())