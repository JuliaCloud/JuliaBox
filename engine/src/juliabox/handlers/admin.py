from datetime import datetime, timedelta

import isodate

from juliabox.cloud.aws import CloudHost
from juliabox.jbox_util import JBoxCfg
from handler_base import JBoxHandler
from juliabox.jbox_container import JBoxContainer
from juliabox.jbox_tasks import JBoxAsyncJob
from juliabox.db import JBoxUserV2, JBoxDynConfig, JBoxDBPlugin


class AdminHandler(JBoxHandler):
    def get(self):
        sessname = self.get_session_id()
        user_id = self.get_user_id()
        if (sessname is None) or (user_id is None):
            self.send_error()
            return

        user = JBoxUserV2(user_id)
        is_admin = sessname in JBoxCfg.get("admin_sessnames", [])
        manage_containers = is_admin or user.has_role(JBoxUserV2.ROLE_MANAGE_CONTAINERS)
        show_report = is_admin or user.has_role(JBoxUserV2.ROLE_ACCESS_STATS)
        cont = JBoxContainer.get_by_name(sessname)

        if cont is None:
            self.send_error()
            return

        if self.handle_if_logout(cont):
            return
        if self.handle_if_stats(is_admin or show_report):
            return
        if self.handle_if_show_cfg(is_admin):
            return
        if self.handle_if_instance_info(is_admin):
            return
        if self.handle_switch_julia_img(user):
            return

        juliaboxver, _upgrade_available = self.get_upgrade_available(cont)

        jimg_type = 0
        if user.has_resource_profile(JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP):
            jimg_type = JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP

        d = dict(
            manage_containers=manage_containers,
            show_report=show_report,
            sessname=sessname,
            user_id=user_id,
            created=isodate.datetime_isoformat(cont.time_created()),
            started=isodate.datetime_isoformat(cont.time_started()),
            allowed_till=isodate.datetime_isoformat((cont.time_started() + timedelta(seconds=JBoxCfg.get('expire')))),
            mem=cont.get_memory_allocated(),
            cpu=cont.get_cpu_allocated(),
            disk=cont.get_disk_allocated(),
            expire=JBoxCfg.get('expire'),
            juliaboxver=juliaboxver,
            jimg_type=jimg_type
        )

        self.rendertpl("ipnbadmin.tpl", d=d)

    def handle_switch_julia_img(self, user):
        switch_julia_img = self.get_argument('switch_julia_img', None)
        if switch_julia_img is None:
            return False
        if user.has_resource_profile(JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP):
            user.unset_resource_profile(JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP)
            new_img_type = 0
        else:
            user.set_resource_profile(JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP)
            new_img_type = JBoxUserV2.RES_PROF_JULIA_PKG_PRECOMP
        user.save()
        response = {'code': 0, 'data': new_img_type}
        self.write(response)
        return True

    def handle_if_show_cfg(self, is_allowed):
        show_cfg = self.get_argument('show_cfg', None)
        if show_cfg is None:
            return False
        if not is_allowed:
            AdminHandler.log_error("Show config not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to view these stats'}
        else:
            response = {'code': 0, 'data': JBoxCfg.nv}
        self.write(response)
        return True

    def handle_if_logout(self, cont):
        logout = self.get_argument('logout', False)
        if logout == 'me':
            JBoxContainer.invalidate_container(cont.get_name())
            JBoxAsyncJob.async_backup_and_cleanup(cont.dockid)
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
                    result = {}
                    # get cluster loads
                    average_load = CloudHost.get_cluster_average_stats('Load')
                    if None != average_load:
                        result['Average Load'] = average_load

                    machine_loads = CloudHost.get_cluster_stats('Load')
                    if None != machine_loads:
                        for n, v in machine_loads.iteritems():
                            result['Instance ' + n] = v
                elif stats == 'sessions':
                    result = {}
                    if CloudHost.ENABLED['autoscale']:
                        instances = CloudHost.get_autoscaled_instances()
                    else:
                        instances = ['localhost']

                    for idx in range(0, len(instances)):
                        inst = instances[idx]
                        result[inst] = JBoxAsyncJob.sync_session_status(inst)['data']
                else:
                    raise Exception("unknown command %s" % (stats,))

                response = {'code': 0, 'data': result}
            except:
                AdminHandler.log_error("exception while getting stats")
                AdminHandler._get_logger().exception("exception while getting stats")
                response = {'code': -1, 'data': 'error getting stats'}

        self.write(response)
        return True

    @staticmethod
    def get_session_stats():
        plugin = JBoxDBPlugin.jbox_get_plugin(JBoxDBPlugin.PLUGIN_USAGE_ACCOUNTING)
        if plugin is None:
            return None

        today = datetime.now()
        week_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
        today_dates = [today]
        stats = {
            'day': plugin.get_stats(today_dates),
            'week': plugin.get_stats(week_dates)
        }
        return stats

    def handle_if_stats(self, is_allowed):
        stats = self.get_argument('stats', None)
        if stats is None:
            return False

        if not is_allowed:
            AdminHandler.log_error("Show stats not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to view these stats'}
        else:
            try:
                if stats == 'stat_sessions':
                    stats = self.get_session_stats()
                else:
                    stats = JBoxDynConfig.get_stat(CloudHost.INSTALL_ID, stats)
                response = {'code': 0, 'data': stats} if stats is not None else {'code': 1, 'data': {}}
            except:
                AdminHandler.log_error("exception while getting stats")
                AdminHandler._get_logger().exception("exception while getting stats")
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
