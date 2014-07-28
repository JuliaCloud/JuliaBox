import docker
import os, sys, time, gzip, isodate, datetime, pytz

def log_info(s):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print (ts + "  " + s)
    sys.stdout.flush()

def esc_sessname(s):
    return s.replace("@", "_at_").replace(".", "_")

def read_config():
    with open("conf/tornado.conf") as f:
        cfg = eval(f.read())

    if os.path.isfile("conf/jdock.user"):
        with open("conf/jdock.user") as f:
            ucfg = eval(f.read())
        cfg.update(ucfg)

    cfg["admin_sessnames"]=[]
    for ad in cfg["admin_users"]:
        cfg["admin_sessnames"].append(esc_sessname(ad))

    cfg["protected_docknames"]=[]
    for ps in cfg["protected_sessions"]:
        cfg["protected_docknames"].append("/" + esc_sessname(ps))

    return cfg

class JDockContainer:
    CONTAINER_PORT_BINDINGS = {8000: ('127.0.0.1',), 8998: ('127.0.0.1',)}
    DCKR = None
    PINGS = {}
    DCKR_IMAGE = None
    MEM_LIMIT = None
    PORTS = [8000, 8998]
    LOCAL_TZ_OFFSET = 0

    def __init__(self, dockid):
        self.dockid = dockid
        self.refresh()

    def refresh(self):
        self.props = None
        self.dbgstr = None
        self.host_ports = None
   
    def get_props(self):
        if None == self.props:
            self.props = JDockContainer.DCKR.inspect_container(self.dockid)
        return self.props
         
    def get_host_ports(self):
        if None == self.host_ports:
            props = self.get_props()
            ports = props['NetworkSettings']['Ports']
            port_map = []
            for port in JDockContainer.PORTS:
                tcp_port = str(port) + '/tcp'
                port_map.append(ports[tcp_port][0]['HostPort'])
            self.host_ports = tuple(port_map)
        return self.host_ports

    def debug_str(self):
        if None == self.dbgstr:
            self.dbgstr = "JDockContainer id=" + str(self.dockid) + ", name=" + str(self.get_name())
        return self.dbgstr
        
    def get_name(self):
        props = self.get_props()
        return props['Name'] if ('Name' in props) else None

    @staticmethod
    def configure(dckr, image, mem_limit):
        JDockContainer.DCKR = dckr
        JDockContainer.DCKR_IMAGE = image
        JDockContainer.MEM_LIMIT = mem_limit
        JDockContainer.LOCAL_TZ_OFFSET = JDockContainer.local_time_offset()

    @staticmethod
    def create_new(name):
        jsonobj = JDockContainer.DCKR.create_container(JDockContainer.DCKR_IMAGE, detach=True, mem_limit=JDockContainer.MEM_LIMIT, ports=JDockContainer.PORTS, name=name)
        dockid = jsonobj["Id"]
        cont = JDockContainer(dockid)
        log_info("Created " + cont.debug_str())
        return cont

    @staticmethod
    def launch_by_name(name, reuse=True):
        log_info("Launching container: " + name)

        cont = JDockContainer.get_by_name(name)

        if (None != cont) and not reuse:
            cont.delete()
            cont = None

        if (None == cont):
            cont = JDockContainer.create_new(name)

        if not cont.is_running():
            cont.start()

        return cont
    
    @staticmethod    
    def maintain(delete_timeout=0, stop_timeout=0, protected_names=[]):
        log_info("Starting container maintenance...")
        tnow = datetime.datetime.now(pytz.utc)
        tmin = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=pytz.utc)

        delete_before = (tnow - datetime.timedelta(seconds=delete_timeout)) if (delete_timeout > 0) else tmin
        stop_before = (tnow - datetime.timedelta(seconds=stop_timeout)) if (stop_timeout > 0) else tmin

        all_containers = JDockContainer.DCKR.containers(all=True)

        for cdesc in all_containers:
            cont = JDockContainer(cdesc['Id'])
            cname = cont.get_name()

            if (cname == None) or (cname in protected_names):
                log_info("Ignoring " + cont.debug_str())
                continue

            c_is_active = cont.is_running()
            last_ping = JDockContainer.get_last_ping(cname)

            # if we don't have a ping record, create one (we must have restarted) 
            if (None == last_ping) and c_is_active:
                log_info("Discovered new container " + cont.debug_str())
                JDockContainer.record_ping(cname)

            if cont.time_started() < delete_before:
                # don't allow running beyond the limit for long running sessions
                log_info("time_started " + str(cont.time_started()) + " delete_before: " + str(delete_before) + " cond: " + str(cont.time_started() < delete_before))
                log_info("Running beyond allowed time " + cont.debug_str())
                cont.delete()
            elif (None != last_ping) and c_is_active and (last_ping < stop_before):
                # if inactive for too long, stop it
                log_info("last_ping " + str(last_ping) + " stop_before: " + str(stop_before) + " cond: " + str(last_ping < stop_before))
                log_info("Inactive beyond allowed time " + cont.debug_str())
                cont.stop()
        log_info("Finished container maintenance.")

    @staticmethod
    def backup_all(loc, name=None):
        log_info("Starting container backup...")

        if name == None:
            all_containers = JDockContainer.DCKR.containers(all=True)
            for cdesc in all_containers:
                cont = JDockContainer(cdesc['Id'])
                cont.backup(loc)
        else:
            cont = JDockContainer.get_by_name(name)
            if None == cont:
                log_info("No container by name " + str(name))
            else:
                cont.backup(loc)

    def backup(self, loc):
        log_info("Backing up " + self.debug_str() + " at " + str(loc))
        cname = self.get_name()
        if cname == None:
            return

        bkup_file = os.path.join(loc, cname[1:] + ".tar.gz")
        if os.path.exists(bkup_file):
            bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + datetime.timedelta(seconds=JDockContainer.LOCAL_TZ_OFFSET)
            tstart = self.time_started()
            tstop = self.time_stopped()
            tcomp = tstart if ((tstop == None) or (tstart > tstop)) else tstop
            if tcomp <= bkup_file_mtime:
                log_info("Already backed up " + self.debug_str())
                return

        bkup_resp = JDockContainer.DCKR.copy(self.dockid, '/home/juser')
        bkup_data = bkup_resp.read(decode_content=True)
        with gzip.open(bkup_file, 'w') as f:
            f.write(bkup_data)
        log_info("Backed up " + self.debug_str() + " into " + bkup_file)

    @staticmethod
    def num_active():
        active_containers = JDockContainer.DCKR.containers(all=False)
        return len(active_containers)

    @staticmethod
    def get_by_name(name):
        nname = "/" + unicode(name)

        for c in JDockContainer.DCKR.containers(all=True):
            if ('Names' in c) and (c['Names'] != None) and (c['Names'][0] == nname):
                return JDockContainer(c['Id'])
        return None

    @staticmethod
    def record_ping(name):
        JDockContainer.PINGS[name] = datetime.datetime.now(pytz.utc)
        #log_info("Recorded ping for " + name)

    @staticmethod
    def get_last_ping(name):
        return JDockContainer.PINGS[name] if (name in JDockContainer.PINGS) else None

    @staticmethod
    def parse_docker_time(tm):
        if None != tm:
            tm = isodate.parse_datetime(tm)
        return tm

    @staticmethod
    def local_time_offset():
        """Return offset of local zone from GMT"""
        if time.localtime().tm_isdst and time.daylight:
            return time.altzone
        else:
            return time.timezone

    def is_running(self):
        props = self.get_props()
        state = props['State']
        return state['Running'] if 'Running' in state else False

    def time_started(self):
        props = self.get_props()
        return JDockContainer.parse_docker_time(props['State']['StartedAt'])

    def time_finished(self):
        props = self.get_props()
        return JDockContainer.parse_docker_time(props['State']['FinishedAt'])

    def time_created(self):
        props = self.get_props()
        return JDockContainer.parse_docker_time(props['Created'])

    def stop(self):
        log_info("Stopping " + self.debug_str())
        self.refresh()
        if self.is_running():
            JDockContainer.DCKR.stop(self.dockid)
            self.refresh()
            log_info("Stopped " + self.debug_str())
        else:
            log_info("Already stopped " + self.debug_str())

    def start(self):
        self.refresh()
        log_info("Starting " + self.debug_str())
        if self.is_running():
            log_info("Already started " + self.debug_str())
            return
        JDockContainer.DCKR.start(self.dockid, port_bindings=JDockContainer.CONTAINER_PORT_BINDINGS)
        self.refresh()
        log_info("Started " + self.debug_str())
        cname = self.get_name()
        if None != cname:
            JDockContainer.record_ping(cname)

    def kill(self):
        log_info("Killing " + self.debug_str())
        JDockContainer.DCKR.kill(self.dockid)
        self.refresh()
        log_info("Killed " + self.debug_str())

    def delete(self):
        self.refresh()
        cname = self.get_name()
        if self.is_running():
            self.kill()
        JDockContainer.DCKR.remove_container(self.dockid)
        if cname != None:
            JDockContainer.PINGS.pop(cname, None)
        log_info("Deleted " + self.debug_str())


dckr = docker.Client()
cfg = read_config()
JDockContainer.configure(dckr, cfg['docker_image'], cfg['mem_limit'])

