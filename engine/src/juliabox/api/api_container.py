__author__ = 'tan'
import time
import sys
import hashlib
import datetime
import pytz
import docker.utils

from juliabox.jbox_container import BaseContainer
from juliabox.jbox_util import JBoxCfg
from juliabox.jbox_tasks import JBoxAsyncJob
from juliabox.cloud import Compute

from api_queue import APIQueue
from api_connector import APIConnector


class APIContainer(BaseContainer):
    NEXT_CONTAINER_ID = 1
    DCKR_IMAGE = None

    # By default all groups have 1024 shares.
    # A group with 100 shares will get a ~10% portion of the CPU time (https://wiki.archlinux.org/index.php/Cgroups)
    CPU_LIMIT = 1024
    MEM_LIMIT = None
    EXPIRE_SECS = 0
    MAX_CONTAINERS = 0
    MAX_PER_API_CONTAINERS = 0

    API_CONTAINERS = dict()
    DESIRED_CONTAINER_COUNTS = {}
    PINGS = {}

    def get_api_name(self):
        name = self.get_name()
        return None if name is None else APIContainer.get_api_name_from_container_name(name)

    @staticmethod
    def configure():
        BaseContainer.DCKR = JBoxCfg.dckr
        APIContainer.DCKR_IMAGE = JBoxCfg.get('api.docker_image')
        APIContainer.MEM_LIMIT = JBoxCfg.get('api.mem_limit')
        APIContainer.CPU_LIMIT = JBoxCfg.get('api.cpu_limit')
        APIContainer.MAX_CONTAINERS = JBoxCfg.get('api.numlocalmax')
        APIContainer.MAX_PER_API_CONTAINERS = JBoxCfg.get('api.numapilocalmax')
        APIContainer.EXPIRE_SECS = JBoxCfg.get('api.expire')

    @staticmethod
    def unique_container_name(api_name):
        nid = str(APIContainer.NEXT_CONTAINER_ID) + BaseContainer.CONTAINER_NAME_SEP + str(time.time())
        if APIContainer.NEXT_CONTAINER_ID >= sys.maxint:
            APIContainer.NEXT_CONTAINER_ID = 1
        else:
            APIContainer.NEXT_CONTAINER_ID += 1

        sign = hashlib.sha1(nid).hexdigest()
        return BaseContainer.CONTAINER_NAME_SEP.join([sign, api_name]) + BaseContainer.SFX_API

    @staticmethod
    def get_api_name_from_container_name(container_name):
        if container_name.startswith("/"):
            container_name = container_name[1:]
        parts = container_name.split(BaseContainer.CONTAINER_NAME_SEP)
        if (len(parts) >= 3) and (parts[-1] == BaseContainer.SFX_API[1:]) and (len(parts[0]) == 40):
            parts.pop(0)
            parts.pop()
            return BaseContainer.CONTAINER_NAME_SEP.join(parts)
        return None

    @staticmethod
    def ensure_container_available(api_name):
        if api_name in APIContainer.API_CONTAINERS:
            containers = APIContainer.API_CONTAINERS[api_name]
            if (len(containers) > 1) or (len(containers) == 1 and APIContainer.get_by_name(containers[0]) is not None):
                APIContainer.log_debug("container already up for %s. count %r", api_name, len(containers))
                return

        APIContainer.log_debug("Launching new %s. None exising: %r", api_name, APIContainer.API_CONTAINERS)
        APIContainer.create_new(api_name)

    @staticmethod
    def create_new(api_name):
        container_name = APIContainer.unique_container_name(api_name)
        queue = APIQueue.get_queue(api_name)
        env = {
            "JBAPI_NAME": api_name,
            "JBAPI_QUEUE": queue.get_endpoint_out(),
            "JBAPI_CMD": queue.get_command(),
            "JBAPI_CID": container_name
        }
        image_name = queue.get_image_name()
        if image_name is None:
            image_name = APIContainer.DCKR_IMAGE

        hostcfg = docker.utils.create_host_config(mem_limit=APIContainer.MEM_LIMIT)

        jsonobj = APIContainer.DCKR.create_container(image_name,
                                                     detach=True,
                                                     host_config=hostcfg,
                                                     cpu_shares=APIContainer.CPU_LIMIT,
                                                     environment=env,
                                                     hostname='juliabox',
                                                     name=container_name)
        dockid = jsonobj["Id"]
        cont = APIContainer(dockid)
        APIContainer.log_info("Created " + cont.debug_str())
        cont.start()
        return cont

    @staticmethod
    def calc_desired_container_counts():
        for api_name in APIContainer.API_CONTAINERS:
            queue = APIQueue.get_queue(api_name, alloc=False)
            if queue is None:
                APIContainer.log_debug("no queue found for api: %s", api_name)
                APIContainer.DESIRED_CONTAINER_COUNTS[api_name] = 0

            desired = APIContainer.DESIRED_CONTAINER_COUNTS[api_name]
            APIContainer.log_debug("re-calculating desired capacity with %s. now %d.", queue.debug_str(), desired)
            if queue.mean_outstanding > 1:
                incr = int(queue.mean_outstanding)
                desired = min(desired + incr, APIContainer.MAX_PER_API_CONTAINERS)
            elif queue.mean_outstanding < 0.01:  # approx 5 polls where 0 q length was found
                desired = 0
            elif queue.mean_outstanding < 0.5 and desired > 1:  # nothing is queued when mean is 1/3
                desired -= 1
            else:
                desired = max(desired, 1)
            APIContainer.DESIRED_CONTAINER_COUNTS[api_name] = desired
            APIContainer.log_debug("calculated desired capacity with %s to %d.", queue.debug_str(), desired)

            if queue.num_outstanding == 0:
                queue.incr_outstanding(0)   # recalculate mean if no requests are coming

    @staticmethod
    def refresh_container_list():
        all_cnames = dict()

        tnow = datetime.datetime.now(pytz.utc)
        tmin = datetime.datetime(datetime.MINYEAR, 1, 1, tzinfo=pytz.utc)
        exp = APIContainer.EXPIRE_SECS
        stop_responded_before = (tnow - datetime.timedelta(seconds=exp)) if (exp > 0) else tmin

        for c in BaseContainer.api_containers(allcontainers=True):
            cid = c['Id']
            cont = APIContainer(cid)
            cname = cont.get_name()
            api_name = cont.get_api_name()
            APIContainer.log_debug("examining container %s (%s), api:%r", cid, cname, api_name)
            if api_name is None:
                continue

            c_is_active = cont.is_running() or cont.is_restarting()
            if not c_is_active:
                cont.delete()
                continue

            APIContainer.register_api_container(api_name, cname)
            last_ping = APIContainer._get_last_ping(cname)
            if (last_ping is not None) and c_is_active and (last_ping < stop_responded_before):
                APIContainer.log_warn("Terminating possibly unresponsive container %s.", cont.debug_str())
                cont.kill()
                cont.delete()
            all_cnames[cname] = cid

        # delete ping entries for non existent containers
        for cname in APIContainer.PINGS.keys():
            if cname not in all_cnames:
                del APIContainer.PINGS[cname]

        # delete non existent containers from container list
        dellist = []
        for (api_name, clist) in APIContainer.API_CONTAINERS.iteritems():
            clist[:] = [x for x in clist if x in all_cnames]
            if len(clist) == 0:
                dellist.append(api_name)

        for api_name in dellist:
            del APIContainer.API_CONTAINERS[api_name]

    @staticmethod
    def release_queues():
        APIContainer.log_debug("active apis: %r", APIContainer.API_CONTAINERS)
        for api_name in APIQueue.QUEUES.keys():
            APIContainer.log_debug("checking queue for %s", api_name)
            if api_name not in APIContainer.API_CONTAINERS:
                APIConnector.release_connectors(api_name)
                APIQueue.release_queue(api_name)

    @staticmethod
    def maintain():
        """
        For each API type, maintain a desired capacity calculated based on number of outstanding requests.
        """
        APIContainer.log_info("Starting container maintenance...")
        APIContainer.refresh_container_list()
        APIContainer.release_queues()
        APIContainer.calc_desired_container_counts()

        def cleanup(msg):
            if 'nid' in msg:
                cont = APIContainer.get_by_name(msg['nid'])
                cont.delete()

        for (api_name, clist) in APIContainer.API_CONTAINERS.iteritems():
            ndiff = len(clist) - APIContainer.DESIRED_CONTAINER_COUNTS[api_name]

            # terminate if in excess
            while ndiff > 0:
                APIContainer.log_debug("terminating one instance of %s", api_name)
                APIConnector.send_terminate_msg(api_name, on_recv=cleanup)
                ndiff -= 1

            # launch if more required
            while ndiff < 0:
                APIContainer.log_debug("launching one instance of %s", api_name)
                APIContainer.create_new(api_name)
                ndiff += 1

        APIContainer.log_info("Finished container maintenance.")

    @staticmethod
    def record_ping(name):
        APIContainer.PINGS[name] = datetime.datetime.now(pytz.utc)
        APIContainer.log_debug("Recorded ping for %s", name)

    @staticmethod
    def _get_last_ping(name):
        return APIContainer.PINGS[name] if (name in APIContainer.PINGS) else None

    @staticmethod
    def get_by_name(name):
        if not name.startswith("/"):
            nname = "/" + unicode(name)
        else:
            nname = unicode(name)

        for c in APIContainer.DCKR.containers(all=True):
            if ('Names' in c) and (c['Names'] is not None) and (c['Names'][0] == nname):
                return APIContainer(c['Id'])
        return None

    @staticmethod
    def register_api_container(api_name, cname):
        clist = APIContainer.API_CONTAINERS[api_name] if api_name in APIContainer.API_CONTAINERS else []
        if cname not in clist:
            clist.append(cname)
            APIContainer.record_ping(cname)

        APIContainer.API_CONTAINERS[api_name] = clist
        if api_name not in APIContainer.DESIRED_CONTAINER_COUNTS:
            APIContainer.DESIRED_CONTAINER_COUNTS[api_name] = 1
        APIContainer.log_info("Registered " + cname)

    @staticmethod
    def deregister_api_container(api_name, cname):
        clist = APIContainer.API_CONTAINERS[api_name] if api_name in APIContainer.API_CONTAINERS else []
        if cname in clist:
            clist.remove(cname)
        APIContainer.API_CONTAINERS[api_name] = clist
        APIContainer.log_info("Deregistered " + cname)

    @staticmethod
    def get_cluster_api_status():
        result = dict()
        for inst in Compute.get_all_instances():
            api_status = JBoxAsyncJob.sync_api_status(inst)
            if api_status['code'] == 0:
                result[inst] = api_status['data']
            else:
                APIContainer.log_error("error fetching api status from %s", inst)
        APIContainer.log_debug("api status: %r", result)
        return result

    def on_start(self):
        APIContainer.register_api_container(self.get_api_name(), self.get_name())

    def before_delete(self, cname, backup):
        APIContainer.deregister_api_container(self.get_api_name(), cname)