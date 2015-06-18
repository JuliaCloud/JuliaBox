__author__ = 'tan'
import os

from juliabox.jbox_util import unquote
from juliabox.handlers import JBoxHandlerPlugin, JBoxUIModulePlugin
from juliabox.jbox_container import JBoxContainer
from juliabox.db import JBoxUserV2
from juliabox.vol import VolMgr
from user_cluster import UserCluster


class ParallelUIModule(JBoxUIModulePlugin):
    provides = [JBoxUIModulePlugin.PLUGIN_CONFIG]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template():
        return os.path.join(ParallelUIModule.TEMPLATE_PATH, "user_cluster_html.tpl")

    @staticmethod
    def get_user_id(handler):
        sessname = unquote(handler.get_cookie("sessname"))
        jbox_cookie = handler.get_session_cookie()

        if (None == sessname) or (len(sessname) == 0) or (None == jbox_cookie):
            handler.send_error()
            return

        user_id = jbox_cookie['u']
        return user_id

    @staticmethod
    def is_allowed(handler):
        user_id = ParallelUIModule.get_user_id(handler)
        user = JBoxUserV2(user_id)
        return user.has_resource_profile(JBoxUserV2.RES_PROF_CLUSTER)


class ParallelHandler(JBoxHandlerPlugin):
    provides = [JBoxHandlerPlugin.PLUGIN_HANDLER, JBoxHandlerPlugin.PLUGIN_JS]

    @staticmethod
    def get_js():
        return "/assets/plugins/parallel/parallel.js"

    @staticmethod
    def get_uri():
        return r"/jboxplugin/par/"

    def get(self):
        return self.post()

    def post(self):
        sessname = unquote(self.get_cookie("sessname"))
        jbox_cookie = self.get_session_cookie()

        if (None == sessname) or (len(sessname) == 0) or (None == jbox_cookie):
            self.send_error()
            return

        mode = self.get_argument('cluster', False)
        if mode is False:
            ParallelHandler.log_error("Unknown mode for parallel handler")
            self.send_error()
            return

        user_id = jbox_cookie['u']
        user = JBoxUserV2(user_id)
        is_allowed = user.has_resource_profile(JBoxUserV2.RES_PROF_CLUSTER)
        if not is_allowed:
            ParallelHandler.log_error("Cluster access not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to use any clusters'}
            self.write(response)
            return True

        cont = JBoxContainer.get_by_name(sessname)
        if cont is None:
            self.send_error()
            return

        ParallelHandler.log_debug("Parallel request %s for %s", mode, cont.debug_str())

        try:
            max_cores = user.get_max_cluster_cores()
            balance = user.get_balance()
            uc = UserCluster(user.get_user_id())
            if mode == 'status':
                status = uc.status()
                status['limits'] = {
                    'max_cores': max_cores,
                    'credits': balance
                }
                self.write_machinefile(cont, uc)
                response = {'code': 0, 'data': status}
            elif mode == 'terminate':
                action = 'terminate' if uc.isactive() else 'delete'
                uc.terminate_or_delete()
                response = {'code': 0, 'data': action}
            elif mode == 'create':
                ninsts = int(self.get_argument('ninsts', 0))
                avzone = self.get_argument('avzone', '')
                spot_price = float(self.get_argument('spot_price', 0.0))
                if ninsts > (max_cores / UserCluster.INSTANCE_CORES):
                    response = {'code': -1, 'data': 'You are allowed a maximum of ' + str(max_cores) + ' cores.'}
                elif (spot_price > UserCluster.INSTANCE_COST) or (spot_price < 0):
                    response = {
                        'code': -1,
                        'data': 'Bid price must be between $0 - $' + str(UserCluster.INSTANCE_COST) + '.'
                    }
                else:
                    uc.delete()
                    user_data = ParallelHandler.create_user_script(cont)
                    uc.create(ninsts, avzone, user_data, spot_price=spot_price)
                    uc.start()
                    response = {'code': 0, 'data': ''}
            else:
                response = {'code': -1, 'data': 'Unknown cluster operation ' + mode}
        except Exception as ex:
            ParallelHandler.log_error("exception in cluster operation")
            ParallelHandler._get_logger().exception("exception in cluster operation")
            response = {'code': -1, 'data': ex.message}

        self.write(response)

    def _write_machinefile(self, cont, filename, machines):
        cluster_hosts = set(machines)
        if len(cluster_hosts) == 0:
            return

        # write out the machinefile on the docker's filesystem
        vol = VolMgr.get_disk_from_container(cont.dockid)
        machinefile = os.path.join(vol.disk_path, ".juliabox", filename)

        existing_hosts = set()
        try:
            with open(machinefile, 'r') as f:
                existing_hosts = set([x.rstrip('\n') for x in f.readlines()])
        except:
            pass

        if cluster_hosts == existing_hosts:
            return

        self.log_debug("writing machinefile for %s to path: %s", cont.debug_str(), machinefile)
        with open(machinefile, 'w') as f:
            for host in cluster_hosts:
                f.write(host+'\n')

    def write_machinefile(self, cont, uc):
        self._write_machinefile(cont, "machinefile", uc.public_ips)
        self._write_machinefile(cont, "machinefile.private", uc.private_ips)

    @staticmethod
    def create_user_script(cont):
        vol = VolMgr.get_disk_from_container(cont.dockid)

        pub_key_file = os.path.join(vol.disk_path, ".ssh", "id_rsa.pub")
        with open(pub_key_file, 'r') as f:
            pub_key = f.read()

        auth_key_file = "/home/juser/.ssh/authorized_keys"
        template = '#! /usr/bin/env bash\n\nsudo -u juser sh -c "echo \\\"%s\\\" >> %s && chmod 600 %s"'
        return template % (pub_key, auth_key_file, auth_key_file)
