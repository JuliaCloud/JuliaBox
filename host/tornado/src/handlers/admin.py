import datetime

import isodate

from jbox_util import unquote
from jbox_handler import JBoxHandler
from jbox_container import JBoxContainer
from handlers.auth import AuthHandler

class AdminHandler(JBoxHandler):
    def get(self):
        sessname = unquote(self.get_cookie("sessname"))
        jbox_cookie = AuthHandler.get_session_cookie(self)
        
        if (None == sessname) or (len(sessname) == 0) or (None == jbox_cookie):
            self.send_error()

        user_id = jbox_cookie['u']
        cont = JBoxContainer.get_by_name(sessname)

        juliaboxver, upgrade_available = self.get_upgrade_available(cont)
        if self.do_upgrade(cont, upgrade_available):
            response = {'code': 0, 'data': ''}
            self.write(response)
            return

        admin_user = (sessname in self.config("admin_sessnames")) or (self.config("admin_sessnames") == [])

        sections = []
        loads = []
        d = dict(
                admin_user=admin_user,
                sessname=sessname, 
                user_id=user_id, 
                created=isodate.datetime_isoformat(cont.time_created()), 
                started=isodate.datetime_isoformat(cont.time_started()),
                allowed_till=isodate.datetime_isoformat((cont.time_started() + datetime.timedelta(seconds=self.config('expire')))),
                mem=cont.get_memory_allocated(), 
                cpu=cont.get_cpu_allocated(),
                disk=cont.get_disk_allocated(),
                expire=self.config('expire'),
                sections=sections,
                loads=loads,
                juliaboxver=juliaboxver,
                upgrade_available=upgrade_available
            )

        if admin_user:
            self.do_admin(sections, loads)

        self.rendertpl("ipnbadmin.tpl", d=d, cfg=self.config())
    
    def do_upgrade(self, cont, upgrade_available):
        upgrade_id = self.get_argument("upgrade_id", '')
        if (upgrade_id == 'me') and (upgrade_available != None):
            cont.stop()
            cont.backup()
            cont.delete()
            return True
        return False

    def get_upgrade_available(self, cont):
        cont_images = cont.get_image_names()
        juliaboxver = cont_images[0]
        if (JBoxContainer.DCKR_IMAGE in cont_images) or ((JBoxContainer.DCKR_IMAGE + ':latest') in cont_images):
            upgrade_available = None
        else:
            upgrade_available = JBoxContainer.DCKR_IMAGE
            if ':' not in upgrade_available:
                upgrade_available = upgrade_available + ':latest'
        return (juliaboxver, upgrade_available)
        
    def do_admin(self, sections, loads):
        iac = []
        ac = []
        sections.append(["Active", ac])
        sections.append(["Inactive", iac])
        
        delete_id = self.get_argument("delete_id", '')
        stop_id = self.get_argument("stop_id", '')
        stop_all = (self.get_argument('stop_all', None) != None)
        
        if stop_all:
            all_containers = JBoxContainer.DCKR.containers(all=False)
            for c in all_containers:
                cont = JBoxContainer(c['Id'])
                cname = cont.get_name()

                if None == cname:
                    log_info("Admin: Not stopping unknown " + cont.debug_str())
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
            o = {}
            o["Id"] = c["Id"][0:12]
            o["Status"] = c["Status"]
            if ("Names" in c) and (c["Names"] != None): 
                o["Name"] = c["Names"][0]
            else:
                o["Name"] = "/None"
            
            if (c["Ports"] == None) or (c["Ports"] == []):
                iac.append(o)
            else:
                ac.append(o)
        
        # get cluster loads
        average_load = CloudHelper.get_cluster_average_stats('Load')
        if None != average_load:
            loads.append({'instance': 'Average', 'load': average_load})
            
        machine_loads = CloudHelper.get_cluster_stats('Load')
        if None != machine_loads:
            for n,v in machine_loads.iteritems():
                loads.append({'instance': n, 'load': v})

