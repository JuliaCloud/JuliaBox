#!/usr/bin/python
 
import tornado.ioloop
import tornado.web
import os, time, sys, shutil, traceback
from gitsync import GitSync

rel_dir = '/'

def read_config():
    with open("conf/tornado.conf") as f:
        cfg = eval(f.read())
    cfg['home_folder'] = os.path.expanduser(cfg['home_folder'])
    return cfg

def rendertpl(rqst, tpl, **kwargs):
    rqst.render("../www/" + tpl, **kwargs)

def log_info(s):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print (ts + "  " + s)
    sys.stdout.flush()

class PingHandler(tornado.web.RequestHandler):
    def get(self):
        log_info('pinghandler ' + str(self.request.uri))
        rendertpl(self, "ping.tpl")


class BrowseHandler(tornado.web.RequestHandler):
    def get(self):
        log_info('browsehandler ' + str(self.request.uri))
        global rel_dir
        fetch_file = self.get_argument('fetch', None)
        if None != fetch_file:
            fetch_file = fetch_file.replace('..', '')
            fetch_file = fetch_file.replace('//', '/')
            file_name = os.path.join(cfg['home_folder'], rel_dir[1:], fetch_file)

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename=' + fetch_file)
            with open(file_name, 'r') as f:
                while True:
                    data = f.read(1024*12)
                    if not data:
                        break
                    self.write(data)
            self.finish()
        else:
            rel_dir = self.get_argument('rel_dir', '/')
            rel_dir = rel_dir.replace('..', '')
            rel_dir = rel_dir.replace('//', '/')
            if rel_dir != '/':
                prev_dir_comps = filter(None, rel_dir.split('/'))
                l = len(prev_dir_comps)
                if l > 0:
                    prev_dir_comps.pop()
                    l -= 1
                prev_dir = '/'
                if l > 0:
                    prev_dir = prev_dir + '/'.join(prev_dir_comps) + '/'
            else:
                prev_dir = ''
            wdir = os.path.join(cfg['home_folder'], rel_dir[1:])
            files = []
            folders = []
            for fname in os.listdir(wdir):
                if fname.startswith('.'):
                    continue
                full_fname = os.path.join(wdir, fname)
                if os.path.isdir(full_fname):
                    folders.append(fname)
                else:
                    files.append(fname)
            rendertpl(self, "upload.tpl", prevdir=prev_dir, currdir=rel_dir, files=files, folders=folders, nfolders=len(folders), nfiles=len(files))


class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        log_info('uploadhandler ' + str(self.request.uri))
        for f in self.request.files['file']:
            file_name = f.filename
            file_contents = f.body
            with open(os.path.join(cfg['home_folder'], rel_dir[1:], file_name), "wb") as fw:
                fw.write(file_contents)
        self.finish()

class SSHKeyHandler(tornado.web.RequestHandler):
    def get(self):
        with open(os.path.expanduser('~/.ssh/id_rsa.pub'), "r") as f:
            response = {
                            'code': 0,
                            'data': f.read()
                        }
            self.write(response)

class SyncHandler(tornado.web.RequestHandler):
    LOC = '~/'
    #LOC = '/tmp/x'
    DEFAULT_BRANCH = 'master'
    def get(self):
        log_info('synchandler ' + str(self.request.uri))
        gitrepos = self.get_git_repos()
        action = self.get_argument('action', None)
        msg = None
        if None != action:
            if action == "addgit":
                git_url = self.get_argument('repo', '').strip()
                git_branch = self.get_argument('branch', '').strip()
                loc = self.get_argument('loc', '').strip()
                try:
                    if len(git_url) > 0:
                        if len(git_branch) == 0:
                            git_branch = SyncHandler.DEFAULT_BRANCH
                        if len(loc) == 0:
                            loc = git_url[(git_url.rindex('/')+1):git_url.rindex('.')]
                        loc = os.path.join(os.path.expanduser(SyncHandler.LOC), loc)
                        gs = GitSync.clone(git_url, loc, True)
                        gs.checkout(git_branch, from_remote=True)
                        gitrepos[gs.repo_hash()] = gs
                        
                        # remove duplicates resulting from modified entries if any
                        delkeys = []
                        for repokey,gs in gitrepos.iteritems():
                            if gs.repo_hash() != repokey:
                                delkeys.append(repokey)
                        for repokey in delkeys:
                            gitrepos.pop(repokey)
                    if git_url.startswith('https://'):
                        msg = ('warning', 'Repository added successfully. Pushing changes to remote repository not supported with HTTP URLs.')
                    else:
                        msg = ('success', 'Repository added successfully')
                except:
                    traceback.print_exc()
                    msg = ('danger', 'Error adding repository')
            elif action == 'delgit':
                try:
                    repo_id = self.get_argument('repo', None)
                    gitrepo = self.get_git_repo(repo_id, gitrepos=gitrepos)
                    if (None != gitrepo) and os.path.exists(gitrepo.loc):
                        shutil.rmtree(gitrepo.loc)
                        gitrepos.pop(repo_id)
                    msg = ('success', 'Repository deleted successfully')
                except:
                    traceback.print_exc()
                    msg = ('danger', 'Error deleting repository')
            elif action == 'syncgit':
                try:
                    repo_id = self.get_argument('repo', None)
                    gitrepo = self.get_git_repo(repo_id, gitrepos=gitrepos)
                    if None != gitrepo:
                        conflicts = gitrepo.sync()
                    if conflicts:
                        msg = ('warning', 'Repository synchronized with some conflicts')
                    else:
                        msg = ('success', 'Repository synchronized successfully')
                except:
                    traceback.print_exc()
                    msg = ('danger', 'Error synchronizing repository')

        rendertpl(self, "sync.tpl", gitrepos=gitrepos, msg=msg)

    def get_git_repos(self):
        gitrepo_paths = GitSync.scan_repo_paths([os.path.expanduser(SyncHandler.LOC)])
        gitrepos = {}
        for repopath in gitrepo_paths:
            gs = GitSync(repopath)
            gitrepos[gs.repo_hash()] = gs
        return gitrepos

    def get_git_repo(self, repokey, gitrepos=None):
        if None == gitrepos:
            gitrepos = self.get_git_repos()
        if repokey in gitrepos:
            return gitrepos[repokey]
        return None
 
cfg = read_config()
 
if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/file-upload", UploadHandler),
        (r"/ping", PingHandler),
        (r"/sync", SyncHandler),
        (r"/sshkey", SSHKeyHandler),
        (r"/", BrowseHandler)
    ])
    application.listen(cfg['port'])
    tornado.ioloop.IOLoop.instance().start()

