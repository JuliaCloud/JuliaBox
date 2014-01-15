import docker
import calendar
import time
import sys

dckr = docker.Client()

def get_num_active_containers():
    return len(dckr.containers(all=False))

def terminate_expired_containers(cfg):
    if cfg["expire"] == 0:
        return
    
    jsonobj = dckr.containers(all=False)
    expired_at = calendar.timegm(time.gmtime()) - cfg["expire"]
    for c in jsonobj:
        if (c["Created"] < expired_at) and not (c["Names"][0] in cfg["protected_docknames"]):
            dckr.kill(c["Id"])
            dckr.remove_container(c["Id"])


def is_container(name, all=True):
    jsonobj = dckr.containers(all=all)
    nname = "/" + unicode(name)
    
    for c in jsonobj:
        if ("Names" in c) and (c["Names"] != None) and (c["Names"][0] == nname) :
            return True, c
        
    return False, None


def launch_container(cfg, name, clear_old_sess, c):
    if c == None:
        iscont, c = is_container(name)
    else:
        iscont = True
        
    id = ""
    
    # kill the container 
    # if it exists and clear_old_sess
    # if it exists and is not in a running state
    
    if iscont and (("Ports" not in c) or (c["Ports"] == None)):
        clear_old_sess = True
    
    if (iscont and clear_old_sess):
        dckr.kill(c["Id"])
        dckr.remove_container(c["Id"])
    
    if ((not iscont) or clear_old_sess) :
        id = create_new_container(cfg, name)
    else:
        id = c["Id"]
    
    uplport, ipnbport = get_container_ports_by_id(id)
    if ipnbport == None :
      return None, None, None
    
    return id, uplport, ipnbport

def get_container_id(name):
    iscont, c = is_container(name)
    if iscont:
        return c.Id, c
    else:
        return None, None


def get_container_ports_by_id(id):
    jsonobj = dckr.inspect_container(id)
    
    # get the mapped ports
    return jsonobj["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"], jsonobj["NetworkSettings"]["Ports"]["8998/tcp"][0]["HostPort"]

def create_new_container(cfg, name):
    jsonobj = dckr.create_container("ijulia", detach=True, mem_limit=cfg["mem_limit"], ports=[8998, 8000], name=name)
    id = jsonobj["Id"]
    dckr.start(id, port_bindings={8998: None, 8000: None})
    return id


def get_container_ports_by_name(name):
    iscont, c = is_container(name)
    
    if not iscont:
        raise Exception ("ERROR: Could not find session : " + name)
    
    return get_container_ports_by_id(c["Id"])


