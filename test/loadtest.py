from locust import HttpLocust, TaskSet, task
import uuid, json, requests, websocket, threading

# enable trace during debug
websocket.enableTrace(True)


class Sightseer(TaskSet):
    """User behavior that just visits different tabs and clicks a few links"""
    def stop_on_error(self, resp):
        if resp.status_code == 0:
            self.stop()
            
    @task(1)    
    def admin(self):
        resp = self.client.get('/hostadmin/')
        self.stop_on_error(resp)

    @task(1)    
    def filesync(self):
        resp = self.client.get('/hostupload/sync')
        self.stop_on_error(resp)

    @task(5)    
    def fileman(self):
        resp = self.client.get('/hostupload/')
        self.stop_on_error(resp)

    @task(1)    
    def console(self):
        resp = self.client.get('/hosteditor/')
        self.stop_on_error(resp)

    @task(3)    
    def ijulia(self):
        resp = self.client.get('/hostipnbsession/')
        self.stop_on_error(resp)

    @task(10)    
    def ping(self):
        resp = self.client.get('/ping/')
        self.stop_on_error(resp)

    @task(2)
    def stop(self):
        self.interrupt()




class NotebookViewer(TaskSet):
    """User behavior that synchronizes a git repo with notebooks and opens them"""
    def stop_on_error(self, resp):
        if resp.status_code == 0:
            self.stop()
            
    def on_start(self):
        self.add_git()
    
    def add_git(self):
        with self.client.post('/hostupload/sync', {'action': 'addgit', 'repo': 'https://github.com/jiahao/ijulia-notebooks.git', 'loc': 'ijulia-notebooks', 'branch': 'master'}, catch_response=True) as resp:
            try:
                resp_json = json.loads(resp.content)
                
                if resp_json['code'] < 0:
                    resp.failure("Ajax failure")
                    self.interrupt()
                    return False
            except:
                resp.failure("Invalid response: [" + resp.content + "]")
                self.interrupt()
        self.ping()
        return True
    
#     @task(1)
#     def sync_git(self):
#         with self.client.post('/hostupload/sync', {'action': 'syncgit', 'repo': 'https://github.com/jiahao/ijulia-notebooks.git'}, catch_response=True) as resp:
#             resp_json = json.loads(resp.content)
#             
#             if resp_json['code'] != 0:
#                 resp.failure("Ajax failure")
#                 self.interrupt()
#                 return False
#         return True
    
    @task(5)
    def navigate_to_notebook(self):
        resp = self.client.get('/tree/ijulia-notebooks/')
        self.stop_on_error(resp)
    
    @task(10)
    def open_notebook1(self):
        resp = self.client.get('/notebooks/ijulia-notebooks/2014-06-09-the-colors-of-chemistry.ipynb')
        self.stop_on_error(resp)
    
    @task(10)
    def open_notebook2(self):
        resp = self.client.get('/notebooks/ijulia-notebooks/2014-06-30-world-of-julia.ipynb')
        self.stop_on_error(resp)
    
    @task(10)
    def open_notebook3(self):
        resp = self.client.get('/notebooks/ijulia-notebooks/2014-08-06-parallel-prefix.ipynb')
        self.stop_on_error(resp)

    @task(10)    
    def ping(self):
        resp = self.client.get('/ping/')
        self.stop_on_error(resp)

    @task(2)
    def stop(self):
        self.interrupt()




# class NotebookRunner(TaskSet):
#     """User behavior that synchronizes a git repo with notebooks and runs all the cells in them"""
#     def stop_on_error(self, resp):
#         if resp.status_code == 0:
#             self.stop()
#             
#     def on_start(self):
#         self.add_git()
#     
#     def add_git(self):
#         with self.client.post('/hostupload/sync', {'action': 'addgit', 'repo': 'https://github.com/jiahao/ijulia-notebooks.git', 'loc': 'ijulia-notebooks', 'branch': 'master'}, catch_response=True) as resp:
#             try:
#                 resp_json = json.loads(resp.content)
#                 
#                 if resp_json['code'] < 0:
#                     resp.failure("Ajax failure")
#                     self.interrupt()
#                     return False
#             except:
#                 resp.failure("Invalid response: [" + resp.content + "]")
#                 self.interrupt()
#         self.ping()
#         return True
# 
#     @task(10)
#     def run_notebook1(self):
#         self.run_notebook('/notebooks/ijulia-notebooks/2014-06-09-the-colors-of-chemistry.ipynb')
#     
#     @task(10)
#     def run_notebook2(self):
#         self.run_notebook('/notebooks/ijulia-notebooks/2014-06-30-world-of-julia.ipynb')
#     
#     @task(10)
#     def run_notebook3(self):
#         self.run_notebook('/notebooks/ijulia-notebooks/2014-08-06-parallel-prefix.ipynb')
# 
#     @task(10)    
#     def ping(self):
#         resp = self.client.get('/ping/')
#         self.stop_on_error(resp)
# 
#     @task(2)
#     def stop(self):
#         self.interrupt()
# 
# 
#     def run_notebook(self, nbpath):
#         """ Bring up kernel and run all cells in a notebook"""
#         kernel_id = None
#         try:
#             kernel_id = NotebookRunner.bring_up(nbpath)
#             NotebookRunner.walk_and_run(ipyurl, kernel_id, NotebookRunner.get_nb(ipyurl, nbpath))
#         except:
#             resp.failure("Error running notebook. kernel_id=" + str(kernel_id) + ", nnpath=" + nbpath)
#             self.interrupt()
#             
#     
#     def bring_up(self, nbpath):
#         """ Bring up a kernel for a notebook returns kernel ID """
#         parts = nbpath.split("/")
#         path = "/".join(parts[0:-1])
#         name = parts[-1]
#         data = json.dumps({"notebook": {"name" : name, "path": path}})
#         with self.client.post('/api/sessions', data=data, catch_response=True) as resp:
#             try:
#                 resp_json = json.loads(resp.content)
#                 return resp_json['kernel']['id']
#             except:
#                 resp.failure("Error running notebook. resp=" + resp.content)
# 
#     @staticmethod
#     def walk_and_run(ipyurl, kernel_id, nbdata):
#         """ Walk through notebook finding code cells and sending execute_request messages"""
#         def get_code(cell):
#             if cell["cell_type"] != "code":
#                 return None
#             return "\n".join(cell["input"])
# 
#         def wsurl(ipyurl, kernel_id, channel):
#             return ipyurl.replace("http://", "ws://") + "/api/kernels/" + kernel_id + "/" + channel
# 
#         def make_msg(code):
#             def header():
#                 # TODO: tweak this? username? session?
#                 return dict(msg_id=str(uuid.uuid4()), username="LoadTest", session="???", msg_type="execute_request")
#             
#             h = header()
#             return dict(
#                 parent_header=h,
#                 header=h,
#                 metadata={},
#                 content=dict(
#                     code=code,
#                     silent=False,
#                     store_history=False,
#                     user_variables=[],
#                     user_expressions={},
#                     allow_stdin=False))
# 
#         cells = reduce(lambda a, b: a+b,
#                        filter(lambda x: x is not None,
#                               map(lambda sheet: map(get_code, sheet["cells"]),
#                                   nbdata["worksheets"])))
#     
#         print "Executing", cells
#         shellurl = wsurl(ipyurl, kernel_id, "shell")
#         print shellurl
#         ws = websocket.create_connection(shellurl)
#         ws.send("LoadTest:???")
#         
#         def execute(code):
#             ws.send(json.dumps(make_msg(code)))
#     
#         def _read(): print ws.recv()
#         
#         threading.Thread(target=_read)
#         map(execute, cells)
#         ws.close()
#     
#     @staticmethod
#     def bring_up(ipyurl, fpath):
#         """ Bring up a kernel for a notebook returns kernel ID """
#         sessionapi = ipyurl + "/api/sessions"
#         parts = fpath.split("/")
#         path = "/".join(parts[0:-1])
#         name = parts[-1]
#         #print sessionapi
#         
#         data = json.dumps({"notebook": {"name" : name, "path": path}})
#         #print repr(data)
# 
#         resp = requests.post(sessionapi, data=data)
#         return resp.json()["kernel"]["id"]
#     
#     @staticmethod
#     def get_nb(ipyurl, fpath):
#         """ Return a json decoded ipynb file. """
#         url = ipyurl + "/files/" + fpath
#         #print url
#         resp = requests.get(url)
#         return resp.json()
        

class MetaBehavior1(TaskSet):
    tasks = {
        #Sightseer: 10,
        NotebookViewer: 5
    }
    
    def on_start(self):
        self.client.get('/')
        self.login()

    def login(self):
        uid = uuid.uuid1().hex
        self.client.get('/hostlaunchipnb/?sessname=' + uid)

        
class JuliaBoxLoad(HttpLocust):
    task_set = MetaBehavior1 
    min_wait = 2000
    max_wait = 10000
