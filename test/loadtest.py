from locust import HttpLocust, TaskSet, task
import uuid, json

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
        resp = self.client.get('/hostshell/')
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
