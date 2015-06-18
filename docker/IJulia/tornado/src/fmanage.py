#!/usr/bin/python

import os
import time
import sys
import shutil
import traceback
import re

import tornado.ioloop
import tornado.web

from gitsync import GitSync
from gdrivesync import GDriveSync


rel_dir = '/'


def read_config():
    with open("conf/tornado.conf") as f:
        cfg_read = eval(f.read())
    cfg_read['home_folder'] = os.path.expanduser(cfg_read['home_folder'])
    return cfg_read


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
                    data = f.read(1024 * 12)
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
            rendertpl(self, "upload.tpl", prevdir=prev_dir, currdir=rel_dir, files=files, folders=folders,
                      nfolders=len(folders), nfiles=len(files))


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


class PkgInfoHandler(tornado.web.RequestHandler):
    def get(self):
        ver = self.get_argument('ver')
        with open(os.path.expanduser('~/.juliabox/' + ver + '_packages.txt'), "r") as f:
            response = {
                'code': 0,
                'data': f.read()
            }
            self.write(response)


class SyncHandler(tornado.web.RequestHandler):
    LOC = '~/'
    # LOC = '/tmp/x'
    DEFAULT_BRANCH = 'master'

    def get(self):
        log_info('synchandler ' + str(self.request.uri))
        gitrepos = SyncHandler.get_git_repos()
        gdrive_repos = SyncHandler.get_gdrive_repos()
        rendertpl(self, "sync.tpl", gitrepos=gitrepos, gdrive_repos=gdrive_repos)

    def post(self):
        log_info('synchandler ' + str(self.request.uri))
        action = self.get_argument('action', None)
        retcode = 0
        if None != action:
            try:
                if action == 'addgdrive':
                    retcode = self.action_addgdrive()
                elif action == 'delgdrive':
                    retcode = self.action_delgdrive()
                elif action == 'syncgdrive':
                    retcode = self.action_syncgdrive()
                elif action == "addgit":
                    retcode = self.action_addgit()
                elif action == 'delgit':
                    retcode = self.action_delgit()
                elif action == 'syncgit':
                    retcode = self.action_syncgit()
            except:
                # TODO: handle auth tok expiry and send out separate error code
                traceback.print_exc()
                retcode = -1
        response = {'code': retcode, 'data': ''}
        self.write(response)

    def action_addgdrive(self):
        self.set_gdrive_auth_tok()
        retcode = 0
        gfolder = self.get_argument('repo', '').strip()
        loc = SyncHandler.sanitize_loc(self.get_argument('loc', '').strip())
        loc = os.path.join(os.path.expanduser(SyncHandler.LOC), loc)
        GDriveSync.clone(gfolder, loc, True)
        return retcode

    def action_delgdrive(self):
        self.set_gdrive_auth_tok()
        repo_id = self.get_argument('repo', None)
        repo = SyncHandler.get_gdrive_repo(repo_id)
        if (None != repo) and os.path.exists(repo.loc):
            shutil.rmtree(repo.loc)
        return 0

    def action_syncgdrive(self):
        self.set_gdrive_auth_tok()
        retcode = 0
        repo_id = self.get_argument('repo', None)
        repo = SyncHandler.get_gdrive_repo(repo_id)
        if None != repo:
            repo.sync()
        return retcode

    def action_syncgit(self):
        retcode = 0
        repo_id = self.get_argument('repo', None)
        gitrepo = self.get_git_repo(repo_id)
        if None != gitrepo:
            if gitrepo.sync():
                log_info('conflicts during sync of repo ' + gitrepo.repo_name())
                retcode = 1  # has conflicts
        return retcode

    def action_delgit(self):
        repo_id = self.get_argument('repo', None)
        gitrepo = self.get_git_repo(repo_id)
        if (None != gitrepo) and os.path.exists(gitrepo.loc):
            shutil.rmtree(gitrepo.loc)
        return 0

    def action_addgit(self):
        retcode = 0
        git_url = self.get_argument('repo', '').strip()
        git_branch = self.get_argument('branch', '').strip()
        loc = SyncHandler.sanitize_loc(self.get_argument('loc', '').strip())
        if len(git_url) == 0:
            retcode = -1
        if (retcode == 0) and (not git_url.startswith('https://')) and (SyncHandler.add_to_ssh_knownhosts(git_url) < 0):
            retcode = -1
        if retcode == 0:
            if len(git_branch) == 0:
                git_branch = SyncHandler.DEFAULT_BRANCH
            if len(loc) == 0:
                loc = git_url[(git_url.rindex('/') + 1):git_url.rindex('.')]
            loc = os.path.join(os.path.expanduser(SyncHandler.LOC), loc)
            gs = GitSync.clone(git_url, loc, True)
            gs.checkout(git_branch, from_remote=True)

            if git_url.startswith('https://'):
                retcode = 1
        return retcode

    @staticmethod
    def add_to_ssh_knownhosts(git_url):
        hostname = git_url.split('@')[1].split(':')[0]
        khfile = os.path.expanduser('~/.ssh/known_hosts')
        fopenmode = 'w'
        if os.path.exists(khfile):
            fopenmode = 'a'
            with open(khfile) as f:
                lines = f.readlines()
                for line in lines:
                    if hostname in line:
                        return 1
        hostname_lines = os.popen('ssh-keyscan -t rsa,dsa ' + hostname).readlines()
        if len(hostname_lines) == 0:
            log_info('ssh-keyscan failed')
            return -1
        with open(khfile, fopenmode) as f:
            for line in hostname_lines:
                f.write(line)
        if fopenmode == 'w':
            os.chmod(khfile, 0644)
        return 0

    @staticmethod
    def get_git_repos():
        gitrepo_paths = GitSync.scan_repo_paths([os.path.expanduser(SyncHandler.LOC)])
        gitrepos = {}
        for repopath in gitrepo_paths:
            gs = GitSync(repopath)
            gitrepos[gs.repo_hash()] = gs
        return gitrepos

    @staticmethod
    def get_git_repo(repokey, gitrepos=None):
        if None == gitrepos:
            gitrepos = SyncHandler.get_git_repos()
        if repokey in gitrepos:
            return gitrepos[repokey]
        return None

    @staticmethod
    def get_gdrive_repos():
        gdriverepo_paths = GDriveSync.scan_repo_paths([os.path.expanduser(SyncHandler.LOC)])
        gdriverepos = {}
        for repopath in gdriverepo_paths:
            gs = GDriveSync(repopath)
            gdriverepos[gs.repo_hash()] = gs
        return gdriverepos

    @staticmethod
    def get_gdrive_repo(repokey, gdriverepos=None):
        if None == gdriverepos:
            gdriverepos = SyncHandler.get_gdrive_repos()
        if repokey in gdriverepos:
            return gdriverepos[repokey]
        return None

    def set_gdrive_auth_tok(self):
        gauth = self.get_argument('gauth', '')
        if len(gauth) > 0:
            GDriveSync.init_creds(gauth)

    @staticmethod
    def sanitize_loc(loc):
        return re.sub(r'^[\.\\\/]*', '', loc)


cfg = read_config()

if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/file-upload", UploadHandler),
        (r"/ping", PingHandler),
        (r"/sync", SyncHandler),
        (r"/sshkey", SSHKeyHandler),
        (r"/pkginfo", PkgInfoHandler),
        (r"/", BrowseHandler)
    ])
    application.listen(cfg['port'])
    tornado.ioloop.IOLoop.instance().start()
