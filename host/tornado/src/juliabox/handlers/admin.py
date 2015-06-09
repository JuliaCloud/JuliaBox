from datetime import datetime, timedelta
import os

import isodate

from juliabox.cloud.aws import CloudHost
from juliabox.jbox_util import unquote
from handler_base import JBoxHandler
from juliabox.jbox_container import JBoxContainer
from juliabox.parallel import UserCluster
from juliabox.jbox_tasks import JBoxAsyncJob
from juliabox.db import JBoxUserV2, JBoxDynConfig, JBoxAccountingV2
from juliabox.vol import VolMgr


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
        use_cluster = is_admin or user.has_resource_profile(JBoxUserV2.RES_PROF_CLUSTER)
        show_report = is_admin or user.has_role(JBoxUserV2.ROLE_ACCESS_STATS)
        cont = JBoxContainer.get_by_name(sessname)

        if cont is None:
            self.send_error()
            return

        # TODO: introduce new role for cluster access 
        if self.handle_if_cluster(user, cont, use_cluster):
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
            use_cluster=use_cluster,
            sessname=sessname,
            user_id=user_id,
            created=isodate.datetime_isoformat(cont.time_created()),
            started=isodate.datetime_isoformat(cont.time_started()),
            allowed_till=isodate.datetime_isoformat((cont.time_started() + timedelta(seconds=self.config('expire')))),
            mem=cont.get_memory_allocated(),
            cpu=cont.get_cpu_allocated(),
            disk=cont.get_disk_allocated(),
            expire=self.config('expire'),
            juliaboxver=juliaboxver,
            jimg_type=jimg_type
        )

        self.rendertpl("ipnbadmin.tpl", d=d, cfg=self.config())

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
            response = {'code': 0, 'data': self.config()}
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

    def write_machinefile(self, cont, uc):
        cluster_hosts = set(uc.public_ips)
        if len(cluster_hosts) == 0:
            return

        # write out the machinefile on the docker's filesystem
        vol = VolMgr.get_disk_from_container(cont.dockid)
        machinefile = os.path.join(vol.disk_path, ".juliabox", "machinefile")

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

    @staticmethod
    def create_user_script(cont):
        vol = VolMgr.get_disk_from_container(cont.dockid)

        pub_key_file = os.path.join(vol.disk_path, ".ssh", "id_rsa.pub")
        with open(pub_key_file, 'r') as f:
            pub_key = f.read()

        auth_key_file = "/home/juser/.ssh/authorized_keys"
        template = '#! /usr/bin/env bash\n\nsudo -u juser sh -c "echo \\\"%s\\\" >> %s && chmod 600 %s"'
        return template % (pub_key, auth_key_file, auth_key_file)

    def handle_if_cluster(self, user, cont, is_allowed):
        mode = self.get_argument('cluster', False)
        if mode is False:
            return False

        if not is_allowed:
            AdminHandler.log_error("Cluser access not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to use any clusters'}
            self.write(response)
            return True

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
                    user_data = AdminHandler.create_user_script(cont)
                    uc.create(ninsts, avzone, user_data, spot_price=spot_price)
                    uc.start()
                    response = {'code': 0, 'data': ''}
            else:
                response = {'code': -1, 'data': 'Unknown cluster operation ' + mode}
        except Exception as ex:
            AdminHandler.log_error("exception in cluster operation")
            AdminHandler._get_logger().exception("exception in cluster operation")
            response = {'code': -1, 'data': ex.message}

        self.write(response)
        return True

    def handle_if_addcluster(self, cont, is_allowed):
        clustername = self.get_argument('addcluster', False)

        if clustername is False:
            return False

        AdminHandler.log_debug("addcluster %s", clustername)
        clustername = clustername.strip()

        if clustername == "":
            return False

        if not is_allowed:
            AdminHandler.log_error("Cluser access not allowed for user")
            response = {'code': -1, 'data': 'You do not have permissions to use any clusters'}
            self.write(response)
            return True
    
        cluster_hosts = CloudHost.get_private_addresses_by_placement_group("juliabox")
        AdminHandler.log_debug("addcluster got hosts: %r", cluster_hosts)
        
        # write out the machinefile on the docker's filesystem
        vol = VolMgr.get_disk_from_container(cont.dockid)
        path = vol.disk_path
        AdminHandler.log_debug("addcluster got diskpath: %s", path)

        machinefile = os.path.join(path, ".juliabox", "machinefile")
        with open(machinefile, 'w') as f:
            for host in cluster_hosts:
                f.write(host+'\n')
        
        response = {'code': 0, 'data': '/home/juser/.juliabox/machinefile'}
        self.write(response)
        return True

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
        today = datetime.now()
        week_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
        today_dates = [today]
        stats = {
            'day': JBoxAccountingV2.get_stats(today_dates),
            'week': JBoxAccountingV2.get_stats(week_dates)
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
