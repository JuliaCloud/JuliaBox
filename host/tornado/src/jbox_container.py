import os, time, gzip, isodate, datetime, pytz, tarfile, sets, json, multiprocessing, psutil
from jbox_accounting import JBoxAccounting
from jbox_util import log_info, CloudHelper

class JBoxContainer:
    CONTAINER_PORT_BINDINGS = {4200: ('127.0.0.1',), 8000: ('127.0.0.1',), 8998: ('127.0.0.1',)}
    HOST_VOLUMES = None
    DCKR = None
    PINGS = {}
    DCKR_IMAGE = None
    MEM_LIMIT = None
    CPU_LIMIT = 1024   # By default all groups have 1024 shares. A group with 100 shares will get a ~10% portion of the CPU time (https://wiki.archlinux.org/index.php/Cgroups)
    PORTS = [4200, 8000, 8998]
    VOLUMES = ['/juliabox']
    LOCAL_TZ_OFFSET = 0
    BACKUP_LOC = None
    BACKUP_BUCKET = None
    MAX_CONTAINERS = 0
    VALID_CONTAINERS = {}

    def __init__(self, dockid):
        self.dockid = dockid
        self.refresh()

    def refresh(self):
        self.props = None
        self.dbgstr = None
        self.host_ports = None
   
    def get_props(self):
        if None == self.props:
            self.props = JBoxContainer.DCKR.inspect_container(self.dockid)
        return self.props
         
    def get_host_ports(self):
        if None == self.host_ports:
            props = self.get_props()
            ports = props['NetworkSettings']['Ports']
            port_map = []
            for port in JBoxContainer.PORTS:
                tcp_port = str(port) + '/tcp'
                port_map.append(ports[tcp_port][0]['HostPort'])
            self.host_ports = tuple(port_map)
        return self.host_ports
    
    def get_cpu_allocated(self):
        props = self.get_props()
        cpu_shares = props['Config']['CpuShares']
        num_cpus = multiprocessing.cpu_count()
        return max(1, int(num_cpus * cpu_shares / 1024))

    def get_memory_allocated(self):
        props = self.get_props()
        mem = props['Config']['Memory']
        if mem > 0:
            return mem
        return psutil.virtual_memory().total

    def debug_str(self):
        if None == self.dbgstr:
            self.dbgstr = "JBoxContainer id=" + str(self.dockid) + ", name=" + str(self.get_name())
        return self.dbgstr
        
    def get_name(self):
        props = self.get_props()
        return props['Name'] if ('Name' in props) else None

    def get_image_names(self):
        props = self.get_props()
        img_id = props['Image']
        for img in JBoxContainer.DCKR.images():
            if img['Id'] == img_id:
                return img['RepoTags']
        return []
        
    @staticmethod
    def configure(dckr, image, mem_limit, cpu_limit, host_volumes, backup_loc, max_containers, backup_bucket=None):
        JBoxContainer.DCKR = dckr
        JBoxContainer.DCKR_IMAGE = image
        JBoxContainer.MEM_LIMIT = mem_limit
        JBoxContainer.CPU_LIMIT = cpu_limit
        JBoxContainer.LOCAL_TZ_OFFSET = JBoxContainer.local_time_offset()
        JBoxContainer.HOST_VOLUMES = host_volumes
        JBoxContainer.BACKUP_LOC = backup_loc
        JBoxContainer.BACKUP_BUCKET = backup_bucket
        JBoxContainer.MAX_CONTAINERS = max_containers

    @staticmethod
    def create_new(name):
        mount_point = os.path.join(JBoxContainer.BACKUP_LOC, name)
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
            os.chmod(mount_point, 0777)
        
        jsonobj = JBoxContainer.DCKR.create_container(JBoxContainer.DCKR_IMAGE, 
                                                      detach=True, 
                                                      mem_limit=JBoxContainer.MEM_LIMIT,
                                                      cpu_shares=JBoxContainer.CPU_LIMIT,
                                                      ports=JBoxContainer.PORTS, 
                                                      volumes=JBoxContainer.VOLUMES, 
                                                      hostname='juliabox',
                                                      name=name)
        dockid = jsonobj["Id"]
        cont = JBoxContainer(dockid)
        log_info("Created " + cont.debug_str())
        cont.create_restore_file()
        return cont

    @staticmethod
    def launch_by_name(name, reuse=True):
        log_info("Launching container: " + name)

        cont = JBoxContainer.get_by_name(name)

        if (None != cont) and not reuse:
            cont.delete()
            cont = None

        if (None == cont):
            cont = JBoxContainer.create_new(name)

        if not cont.is_running():
            cont.start()
        else:
            cont.restart()

        JBoxContainer.publish_container_stats()
        return cont        

    @staticmethod
    def publish_container_stats():
        """ Publish custom cloudwatch statistics. Used for status monitoring and auto scaling. """
        nactive = JBoxContainer.num_active()
        CloudHelper.publish_stats("NumActiveContainers", "Count", nactive)
        
        cpu_used_pct = psutil.cpu_percent()
        
        mem_used_pct = psutil.virtual_memory().percent
        CloudHelper.publish_stats("MemUsed", "Percent", mem_used_pct)
        
        disk_used_pct = 0
        for x in psutil.disk_partitions():
            disk_used_pct = max(psutil.disk_usage(x.mountpoint).percent, disk_used_pct)
        CloudHelper.publish_stats("DiskUsed", "Percent", disk_used_pct)
        
        cont_load_pct = min(100, max(0, nactive * 100 / JBoxContainer.MAX_CONTAINERS))
        CloudHelper.publish_stats("ContainersUsed", "Percent", cont_load_pct)
        
        CloudHelper.publish_stats("Load", "Percent", max(cont_load_pct, disk_used_pct, mem_used_pct, cpu_used_pct))

    
    @staticmethod    
    def maintain(delete_timeout=0, delete_stopped_timeout=0, stop_timeout=0, protected_names=[]):
        log_info("Starting container maintenance...")
        tnow = datetime.datetime.now(pytz.utc)
        tmin = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=pytz.utc)

        delete_before = (tnow - datetime.timedelta(seconds=delete_timeout)) if (delete_timeout > 0) else tmin
        stop_before = (tnow - datetime.timedelta(seconds=stop_timeout)) if (stop_timeout > 0) else tmin
        delete_stopped_before = tnow - datetime.timedelta(seconds=delete_stopped_timeout) if (delete_stopped_timeout > 0) else tmin

        all_containers = JBoxContainer.DCKR.containers(all=True)
        all_cnames = {}
        for cdesc in all_containers:
            cid = cdesc['Id']
            cont = JBoxContainer(cid)
            cname = cont.get_name()
            all_cnames[cname] = cid

            if (cname == None) or (cname in protected_names):
                log_info("Ignoring " + cont.debug_str())
                continue

            c_is_active = cont.is_running()
            last_ping = JBoxContainer.get_last_ping(cname)

            # if we don't have a ping record, create one (we must have restarted) 
            if (None == last_ping) and c_is_active:
                log_info("Discovered new container " + cont.debug_str())
                JBoxContainer.record_ping(cname)

            if cont.time_started() < delete_before:
                # don't allow running beyond the limit for long running sessions
                #log_info("time_started " + str(cont.time_started()) + " delete_before: " + str(delete_before) + " cond: " + str(cont.time_started() < delete_before))
                log_info("Running beyond allowed time " + cont.debug_str())
                cont.delete()
            elif (None != last_ping) and c_is_active and (last_ping < stop_before):
                # if inactive for too long, stop it
                #log_info("last_ping " + str(last_ping) + " stop_before: " + str(stop_before) + " cond: " + str(last_ping < stop_before))
                log_info("Inactive beyond allowed time " + cont.debug_str())
                cont.stop()
            elif (not c_is_active) and (cont.time_finished() < delete_stopped_before):
                log_info("Deleting stopped container " + cont.debug_str())
                cont.delete()

        # delete ping entries for non exixtent containers
        for cname in JBoxContainer.PINGS.keys():
            if cname not in all_cnames:
                del JBoxContainer.PINGS[cname]
        
        JBoxContainer.VALID_CONTAINERS = all_cnames
        JBoxContainer.publish_container_stats()
        log_info("Finished container maintenance.")
    
    @staticmethod
    def is_valid_container(cname, hostports):
        cont = None
        if cname in JBoxContainer.VALID_CONTAINERS:
            try:
                cont = JBoxContainer(JBoxContainer.VALID_CONTAINERS[cname])
            except:
                pass
        else:
            all_containers = JBoxContainer.DCKR.containers(all=True)
            for cdesc in all_containers:
                cid = cdesc['Id']
                cont = JBoxContainer(cid)
                cont_name = cont.get_name()
                JBoxContainer.VALID_CONTAINERS[cont_name] = cid
                if cname == cont_name:
                    break
        
        if cont == None:
            return False
        
        try:
            return (hostports == cont.get_host_ports())
        except:
            return False
    
    @staticmethod
    def pull_from_s3(local_file, metadata_only=False):
        if None == JBoxContainer.BACKUP_BUCKET:
            return None
        return CloudHelper.pull_file_from_s3(JBoxContainer.BACKUP_BUCKET, local_file, metadata_only=metadata_only)

    @staticmethod
    def backup_all():
        log_info("Starting container backup...")
        all_containers = JBoxContainer.DCKR.containers(all=True)
        for cdesc in all_containers:
            cont = JBoxContainer(cdesc['Id'])
            cont.backup()

    def backup(self):
        log_info("Backing up " + self.debug_str() + " at " + str(JBoxContainer.BACKUP_LOC))
        cname = self.get_name()
        if cname == None:
            return

        bkup_file = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:] + ".tar.gz")
        
        if not self.is_running():
            k = JBoxContainer.pull_from_s3(bkup_file, True)
            bkup_file_mtime = None
            if os.path.exists(bkup_file):
                bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + datetime.timedelta(seconds=JBoxContainer.LOCAL_TZ_OFFSET)
            elif None != k:
                bkup_file_mtime = JBoxContainer.parse_iso_time(k.get_metadata('backup_time'))
    
            if None != bkup_file_mtime:
                tstart = self.time_started()
                tstop = self.time_finished()
                tcomp = tstart if ((tstop == None) or (tstart > tstop)) else tstop
                if tcomp <= bkup_file_mtime:
                    log_info("Already backed up " + self.debug_str())
                    return

        bkup_resp = JBoxContainer.DCKR.copy(self.dockid, '/home/juser/')
        bkup_data = bkup_resp.read(decode_content=True)
        with gzip.open(bkup_file, 'w') as f:
            f.write(bkup_data)
        log_info("Backed up " + self.debug_str() + " into " + bkup_file)
        self.filter_backup_file()
        
        # Upload to S3 if so configured. Delete from local if successful.
        bkup_file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(bkup_file), pytz.utc) + datetime.timedelta(seconds=JBoxContainer.LOCAL_TZ_OFFSET)
        if None != JBoxContainer.BACKUP_BUCKET:
            if None != CloudHelper.push_file_to_s3(JBoxContainer.BACKUP_BUCKET, bkup_file, metadata={'backup_time': bkup_file_mtime.isoformat()}):
                os.remove(bkup_file)
                log_info("Moved backup to S3 " + self.debug_str())

    def filter_backup_file(self):
        cname = self.get_name()
        src = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:] + ".tar.gz")
        dest = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:] + "_filtered.tar.gz")
        log_info("Filtering required files from backup " + src + " to " + dest)
        
        src_tar = tarfile.open(src, 'r:gz')
        dest_tar = tarfile.open(dest, 'w:gz')
        for info in src_tar.getmembers():
            if info.name.startswith('juser/.') and not (info.name.startswith('juser/.ssh') or info.name.startswith('juser/.juliabox')):
                continue
            if info.name.startswith('juser/resty'):
                continue
            dest_tar.addfile(info, src_tar.extractfile(info))
        src_tar.close()
        dest_tar.close()
        os.chmod(dest, 0666)
        log_info("Created filtered file " + dest)

        # delete local copy of backup if we have it on s3
        os.remove(src)
        os.rename(dest, src)

    def create_restore_file(self):
        cname = self.get_name()
        if cname == None:
            return
        
        src = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:] + ".tar.gz")
        k = JBoxContainer.pull_from_s3(src)     # download from S3 if exists
        if not os.path.exists(src):
            return

        dest = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:], "restore.tar.gz")
        log_info("Filtering out restore info from backup " + src + " to " + dest)

        src_tar = tarfile.open(src, 'r:gz')
        dest_tar = tarfile.open(dest, 'w:gz')
        for info in src_tar.getmembers():
            if info.name.startswith('juser/.') and not info.name.startswith('juser/.ssh'):
                continue
            if info.name.startswith('juser/resty'):
                continue
            info.name = info.name[6:]
            if len(info.name) == 0:
                continue
            dest_tar.addfile(info, src_tar.extractfile(info))
        src_tar.close()
        dest_tar.close()
        os.chmod(dest, 0666)
        log_info("Created restore file " + dest)

        # delete local copy of backup if we have it on s3
        if None != k:
            os.remove(src)

    @staticmethod
    def num_active():
        active_containers = JBoxContainer.DCKR.containers(all=False)
        return len(active_containers)

    @staticmethod
    def get_by_name(name):
        nname = "/" + unicode(name)

        for c in JBoxContainer.DCKR.containers(all=True):
            if ('Names' in c) and (c['Names'] != None) and (c['Names'][0] == nname):
                return JBoxContainer(c['Id'])
        return None

    @staticmethod
    def record_ping(name):
        JBoxContainer.PINGS[name] = datetime.datetime.now(pytz.utc)
        #log_info("Recorded ping for " + name)

    @staticmethod
    def get_last_ping(name):
        return JBoxContainer.PINGS[name] if (name in JBoxContainer.PINGS) else None

    @staticmethod
    def parse_iso_time(tm):
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
        return JBoxContainer.parse_iso_time(props['State']['StartedAt'])

    def time_finished(self):
        props = self.get_props()
        return JBoxContainer.parse_iso_time(props['State']['FinishedAt'])

    def time_created(self):
        props = self.get_props()
        return JBoxContainer.parse_iso_time(props['Created'])

    def stop(self):
        log_info("Stopping " + self.debug_str())
        self.refresh()
        if self.is_running():
            JBoxContainer.DCKR.stop(self.dockid, timeout=5)
            self.refresh()
            log_info("Stopped " + self.debug_str())
            self.record_usage()
        else:
            log_info("Already stopped " + self.debug_str())

    def start(self):
        self.refresh()
        log_info("Starting " + self.debug_str())
        if self.is_running():
            log_info("Already started " + self.debug_str())
            return

        vols = {}
        for hvol,cvol in zip(JBoxContainer.HOST_VOLUMES, JBoxContainer.VOLUMES):
            hvol = hvol.replace('${CNAME}', self.get_name())
            vols[hvol] = {'bind': cvol, 'ro': False}

        JBoxContainer.DCKR.start(self.dockid, port_bindings=JBoxContainer.CONTAINER_PORT_BINDINGS, binds=vols)
        self.refresh()
        log_info("Started " + self.debug_str())
        cname = self.get_name()
        if None != cname:
            JBoxContainer.record_ping(cname)
    
    def restart(self):
        self.refresh()
        log_info("Restarting " + self.debug_str())
        JBoxContainer.DCKR.restart(self.dockid, timeout=5)
        self.refresh()
        log_info("Restarted " + self.debug_str())
        cname = self.get_name()
        if None != cname:
            JBoxContainer.record_ping(cname)
        
    def kill(self):
        log_info("Killing " + self.debug_str())
        JBoxContainer.DCKR.kill(self.dockid)
        self.refresh()
        log_info("Killed " + self.debug_str())
        self.record_usage()

    def delete(self):
        log_info("Deleting " + self.debug_str())
        self.refresh()
        cname = self.get_name()
        if self.is_running():
            self.kill()
        JBoxContainer.DCKR.remove_container(self.dockid)
        if cname != None:
            JBoxContainer.PINGS.pop(cname, None)
        log_info("Deleted " + self.debug_str())
        # remove mount point
        try:
            mount_point = os.path.join(JBoxContainer.BACKUP_LOC, cname[1:])
            os.rmdir(mount_point)
            log_info("Removed mount point " + mount_point)
        except:
            log_info("Error removing mount point " + self.debug_str())

    def record_usage(self):
        start_time = self.time_created()
        finish_time = self.time_finished()
        duration = (finish_time - start_time).total_seconds()
        acct = JBoxAccounting(self.get_name(), duration, json.dumps(self.get_image_names()), time_stopped=finish_time.isoformat())
        acct.save()
