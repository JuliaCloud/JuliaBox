from datetime import datetime, timedelta

import isodate
from cloud.aws import CloudHost

from jbox_util import unquote
from handlers.handler_base import JBoxHandler
from jbox_container import JBoxContainer
from db import JBoxUserV2, JBoxDynConfig, JBoxAccountingV2, JBoxInvite


class AdminHandler(JBoxHandler):
    def get(self):
        sessname = unquote(self.get_cookie("sessname"))
        jbox_cookie = self.get_session_cookie()

        if (None == sessname) or (len(sessname) == 0) or (None == jbox_cookie):
            self.send_error()
            return

        user_id = jbox_cookie['u']
        user = JBoxUserV2(user_id)
        is_admin = sessname in self.config("admin_sessnames", [])
        manage_containers = is_admin or user.has_role(JBoxUserV2.ROLE_MANAGE_CONTAINERS)
        show_report = is_admin or user.has_role(JBoxUserV2.ROLE_ACCESS_STATS)
        cont = JBoxContainer.get_by_name(sessname)

        if cont is None:
            self.send_error()
            return

        if self.handle_if_logout(cont):
            return
        if self.handle_if_stats(is_admin):
            return
        if self.handle_if_show_cfg(is_admin):
            return
        if self.handle_if_instance_info(is_admin):
            return

        juliaboxver, _upgrade_available = self.get_upgrade_available(cont)

        sections = []
        report = {}
        report_span = 'day'

        if manage_containers:
            sections = self.do_containers()

        if show_report:
            today = datetime.now()
            if self.get_argument('range', 'day') == 'week':
                dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
                report_span = 'week'
            else:
                dates = [today]
            report = JBoxAccountingV2.get_stats(dates)

        d = dict(
            manage_containers=manage_containers,
            show_report=show_report,
            report_span=report_span,
            sessname=sessname,
            user_id=user_id,
            created=isodate.datetime_isoformat(cont.time_created()),
            started=isodate.datetime_isoformat(cont.time_started()),
            allowed_till=isodate.datetime_isoformat((cont.time_started() + timedelta(seconds=self.config('expire')))),
            mem=cont.get_memory_allocated(),
            cpu=cont.get_cpu_allocated(),
            disk=cont.get_disk_allocated(),
            expire=self.config('expire'),
            sections=sections,
            report=report,
            juliaboxver=juliaboxver
        )

        self.rendertpl("ipnbadmin.tpl", d=d, cfg=self.config())

    def handle_if_show_cfg(self, is_allowed):
        show_cfg = self.get_argument('show_cfg', None)
        if show_cfg is None:
            return False
        if not is_allowed:
            AdminHandler.log_error("Show config not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to view these stats'}
        else:
            response = {'code': 0, 'data': self.config()}
        self.write(response)
        return True

    def handle_if_logout(self, cont):
        logout = self.get_argument('logout', False)
        if logout == 'me':
            cont.async_backup_and_cleanup()
            response = {'code': 0, 'data': ''}
            self.write(response)
            return True
        return False

    def handle_if_instance_info(self, is_allowed):
        stats = self.get_argument('instance_info', None)
        if stats is None:
            return False

        if not is_allowed:
            AdminHandler.log_error("Show instance info not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to view these stats'}
        else:
            try:
                if stats == 'load':
                    stats = {}
                    # get cluster loads
                    average_load = CloudHost.get_cluster_average_stats('Load')
                    if None != average_load:
                        stats['Average Load'] = average_load;

                    machine_loads = CloudHost.get_cluster_stats('Load')
                    if None != machine_loads:
                        for n, v in machine_loads.iteritems():
                            stats['Instance ' + n] = v

                response = {'code': 0, 'data': stats} if stats is not None else {'code': 1, 'data': {}}
            except:
                AdminHandler.log_error("exception while getting stats")
                response = {'code': -1, 'data': 'error getting stats'}

        self.write(response)
        return True

    def handle_if_stats(self, is_allowed):
        stats = self.get_argument('stats', None)
        if stats is None:
            return False

        if not is_allowed:
            AdminHandler.log_error("Show stats not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to view these stats'}
        else:
            try:
                stats = JBoxDynConfig.get_stat(CloudHost.INSTALL_ID, stats)
                response = {'code': 0, 'data': stats} if stats is not None else {'code': 1, 'data': {}}
            except:
                AdminHandler.log_error("exception while getting stats")
                response = {'code': -1, 'data': 'error getting stats'}

        self.write(response)
        return True

    @staticmethod
    def get_upgrade_available(cont):
        cont_images = cont.get_image_names()
        juliaboxver = cont_images[0]
        if (JBoxContainer.DCKR_IMAGE in cont_images) or ((JBoxContainer.DCKR_IMAGE + ':latest') in cont_images):
            upgrade_available = None
        else:
            upgrade_available = JBoxContainer.DCKR_IMAGE
            if ':' not in upgrade_available:
                upgrade_available += ':latest'
        return juliaboxver, upgrade_available

    def do_containers(self):
        sections = []

        iac = []
        ac = []
        sections.append(["Active", ac])
        sections.append(["Inactive", iac])

        delete_id = self.get_argument("delete_id", '')
        stop_id = self.get_argument("stop_id", '')
        stop_all = (self.get_argument('stop_all', None) is not None)

        if stop_all:
            all_containers = JBoxContainer.DCKR.containers(all=False)
            for c in all_containers:
                cont = JBoxContainer(c['Id'])
                cname = cont.get_name()

                if None == cname:
                    self.log_info("Admin: Not stopping unknown " + cont.debug_str())
                elif cname not in self.config("protected_docknames"):
                    cont.stop()

        elif not (stop_id == ''):
            cont = JBoxContainer(stop_id)
            cont.stop()
        elif not (delete_id == ''):
            cont = JBoxContainer(delete_id)
            cont.delete()

        # get them all again (in case we deleted some)
        jsonobj = JBoxContainer.DCKR.containers(all=all)
        for c in jsonobj:
            o = dict()
            o["Id"] = c["Id"][0:12]
            o["Status"] = c["Status"]
            if ("Names" in c) and (c["Names"] is not None):
                o["Name"] = c["Names"][0]
            else:
                o["Name"] = "/None"

            if (c["Ports"] is None) or (c["Ports"] == []):
                iac.append(o)
            else:
                ac.append(o)

        return sections
