__author__ = 'tan'
import os

from juliabox.handlers import JBoxHandlerPlugin, JBoxUIModulePlugin
from juliabox.jbox_tasks import JBoxdPlugin, JBoxAsyncJob
from juliabox.jbox_container import JBoxContainer
from juliabox.db import JBoxUserV2
from juliabox.vol import JBoxVol
from juliabox.plugins.compute_ec2 import CompEC2

from ebs import JBoxEBSVol
from disk_state_tbl import JBoxDiskState


class JBoxEBSVolAsyncTask(JBoxdPlugin):
    provides = [JBoxdPlugin.PLUGIN_CMD]

    @staticmethod
    def do_task(plugin_name, plugin_type, data):
        if plugin_name != JBoxEBSVolAsyncTask.__name__ or plugin_type != JBoxdPlugin.PLUGIN_CMD:
            return
        mode = data['action']
        user_id = data['user_id']
        sessname = data['sessname']

        user = JBoxUserV2(user_id)
        is_allowed = user.has_resource_profile(JBoxUserV2.RES_PROF_DISK_EBS_10G)
        if not is_allowed:
            JBoxEBSVolAsyncTask.log_error("Data volume access not allowed for user")
            return

        cont = JBoxContainer.get_by_name(sessname)
        if cont is None:
            return

        vol = JBoxEBSVol.get_disk_from_container(sessname)
        disk_state = None
        try:
            disk_state = JBoxDiskState(cluster_id=CompEC2.INSTALL_ID, region_id=CompEC2.REGION, user_id=user_id)
        except:
            pass

        JBoxEBSVolAsyncTask.log_debug("Data volume request %s for %s", mode, cont.debug_str())

        if mode == 'attach':
            if vol is None:
                vol = JBoxEBSVol.get_disk_for_user(user_id)
                JBoxEBSVol.mount_host_device(vol.disk_path, cont.dockid, JBoxVol.DATA_MOUNT_POINT)
                disk_state = JBoxDiskState(cluster_id=CompEC2.INSTALL_ID, region_id=CompEC2.REGION, user_id=user_id)
                if disk_state.get_state() != JBoxDiskState.STATE_ATTACHED:
                    disk_state.set_state(JBoxDiskState.STATE_ATTACHED)
                    disk_state.save()
        elif mode == 'detach':
            if cont is not None and cont.is_running():
                if vol is not None:
                    # unmount from container first
                    JBoxEBSVol.unmount_host_device(vol.disk_path, cont.dockid)
                elif disk_state is not None:
                    # no volume attached. ensure disk state is updated
                    if disk_state.get_state() != JBoxDiskState.STATE_DETACHED:
                        disk_state.set_state(JBoxDiskState.STATE_DETACHED)
                        disk_state.save()
            if vol is not None:
                vol.release(backup=True)

        JBoxEBSVolAsyncTask.log_debug("Data volume request %s completed for %s", mode, cont.debug_str())


class JBoxEBSVolUIModule(JBoxUIModulePlugin):
    provides = [JBoxUIModulePlugin.PLUGIN_CONFIG]
    TEMPLATE_PATH = os.path.dirname(__file__)

    @staticmethod
    def get_template(plugin_type):
        if plugin_type == JBoxUIModulePlugin.PLUGIN_CONFIG:
            return os.path.join(JBoxEBSVolUIModule.TEMPLATE_PATH, "vol_ebs_html.tpl")
        return None

    @staticmethod
    def get_user_id(handler):
        sessname = handler.get_session_id()
        user_id = handler.get_user_id()
        if (sessname is None) or (user_id is None):
            handler.send_error()
            return
        return user_id

    @staticmethod
    def is_allowed(handler):
        user_id = JBoxEBSVolUIModule.get_user_id(handler)
        user = JBoxUserV2(user_id)
        return user.has_resource_profile(JBoxUserV2.RES_PROF_DISK_EBS_10G)


class JBoxEBSVolHandler(JBoxHandlerPlugin):
    provides = [JBoxHandlerPlugin.PLUGIN_HANDLER, JBoxHandlerPlugin.PLUGIN_JS]

    @staticmethod
    def get_js():
        return "/assets/plugins/vol_ebs/vol_ebs.js"

    @staticmethod
    def register(app):
        app.add_handlers(".*$", [(r"/jboxplugin/ebsdatavol/", JBoxEBSVolHandler)])

    def get(self):
        return self.post()

    def post(self):
        sessname = self.get_session_id()
        user_id = self.get_user_id()
        if (sessname is None) or (user_id is None):
            self.send_error()
            return

        mode = self.get_argument('action', False)
        if mode is False:
            JBoxEBSVolHandler.log_error("Unknown mode for ebs handler")
            self.send_error()
            return

        try:
            if mode == 'attach' or mode == 'detach':
                JBoxAsyncJob.async_plugin_task(JBoxEBSVolAsyncTask.__name__, {
                    'action': mode,
                    'user_id': user_id,
                    'sessname': sessname
                })
                response = {'code': 0, 'data': ''}
            elif mode == 'status':
                response = {'code': 0, 'data': self._get_state(sessname, user_id)}
            else:
                response = {'code': -1, 'data': 'Unknown data volume operation ' + mode}
        except Exception as ex:
            JBoxEBSVolHandler.log_error("exception in data volume operation")
            JBoxEBSVolHandler._get_logger().exception("exception in data volume operation")
            response = {'code': -1, 'data': ex.message}

        self.write(response)

    def _get_state(self, sessname, user_id):
        vol = JBoxEBSVol.get_disk_from_container(sessname)
        state_code = JBoxDiskState.STATE_DETACHED
        try:
            disk_state = JBoxDiskState(cluster_id=CompEC2.INSTALL_ID, region_id=CompEC2.REGION, user_id=user_id)
            state_code = disk_state.get_state()
        except:
            pass

        if ((state_code == JBoxDiskState.STATE_ATTACHED) and (vol is None)) or \
                ((state_code == JBoxDiskState.STATE_DETACHED) and (vol is not None)):
            state_code = -1

        self.log_debug("EBS disk state: %r", state_code)
        return {
            'disk_size': '10 GB',
            'state': state_code
        }