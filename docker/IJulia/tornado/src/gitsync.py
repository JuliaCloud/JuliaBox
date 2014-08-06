# keeps folders synchronized with a git repository
# not perfect yet. complex merging problematic. git commands can be brittle across versions.
import git, os, datetime, pytz, shutil, string, hashlib

class GitSync:
    def __init__(self, loc):
        self.loc = loc
        self.repo = git.Repo(loc)

    def repo_hash(self):
        return hashlib.sha1('_'.join([self.loc, self.remote_url(), self.branch_name()])).hexdigest()
        
    def repo_name(self):
        return os.path.basename(self.loc) + ' (' + self.remote_url() + ' - ' + self.branch_name() + ')'

    def remote_name(self):
        return self.repo.remote().name

    def remote_url(self):
        return self.repo.remotes[self.remote_name()].url

    def branch_name(self):
        return self.repo.active_branch.name

    def remote_branch_name(self):
        return self.remote_name() + '/' + self.branch_name()

    def local_branches(self):
        return [x.split(' ')[-1] for x in self.repo.git.branch().split('\n')]

    def is_dirty(self):
        return self.repo.is_dirty()

    def has_commits_to_sync(self, output=None):
        gitresult = self.repo.git.log(self.remote_branch_name() + '..', '--oneline').strip()
        if None != output:
            output.append(gitresult)
        return (len(gitresult) > 0)
        
    def get_commits_to_sync(self):
        output = []
        if not self.has_commits_to_sync(output):
            return []
        return output.pop().split('\n')

    def num_commits_to_sync(self):
        return len(self.get_commits_to_sync())

    def has_untracked_files(self, output=None):
        status = self.repo.git.status()
        if None != output:
            output.append(status)
        return ('Untracked files:' in status)

    def get_untracked_files(self):
        output = []
        if not self.has_untracked_files(output):
            return []
        
        untf = output.pop().split('Untracked files:')[1][1:].split("\n")
        return [x[1:] for x in untf if string.strip(x) != "" and x.startswith("\t")]

    def num_untracked_files(self):
        return len(self.get_untracked_files())

    def sync(self, msg=None):
        g = self.repo.git

        if self.has_untracked_files():
            g.add('.')

        has_changes = self.is_dirty()
        if has_changes:
            g.stash()

        try:
            g.pull()
        except:
            pass

        has_conflicts = False
        if has_changes:
            try:
                g.stash('pop')
            except:
                has_conflicts = True
                diff = g.stash('show', '-p')
                with open(os.path.join(self.loc, 'conflict.diff'), 'w') as f:
                    f.write(diff)
                g.stash('drop')
            g.add('.')
            if None == msg:
                msg = 'juliabox ' + str(datetime.datetime.now(pytz.utc))
            g.commit(m=msg)

        if (self.num_commits_to_sync() > 0) and (not self.remote_url().startswith('https://')):
            g.push('-u', self.remote_name(), self.branch_name())

        return has_conflicts

    def delete_branch(self, branch, local=True, remote=False, force=False):
        g = self.repo.git
        if local:
            if force:
                g.branch('-D', branch)
            else:
                g.branch('--delete', branch)
        if remote:
            g.push(self.remote_name(), ':'+branch)

    def checkout(self, branch, from_remote=False):
        if self.branch_name() == branch:
            return
        
        if from_remote:
            if branch in self.local_branches():
                self.delete_branch(branch, local=True, remote=False)
            remote_branch_name = self.remote_name() + '/' + branch
            self.repo.git.checkout(remote_branch_name, b=branch)
        else:
            if branch in self.local_branches():
                self.repo.git.checkout(branch)
            else:
                self.repo.git.checkout(b=branch)

    @staticmethod
    def clone(src, loc, overwrite=False):
        if overwrite and os.path.exists(loc):
            shutil.rmtree(loc)
        repo = git.Repo.clone_from(src, loc)
        if repo != None:
            return GitSync(loc)
        return None

    @staticmethod
    def scan_repo_paths(dirs):
        repos = []
        for d in dirs:
            for pth in os.listdir(d):
                if pth.startswith('.'):
                    continue
                fpth = os.path.join(d, pth)
                if os.path.isdir(fpth):
                    git_pth = os.path.join(fpth, '.git')
                    if os.path.isdir(git_pth):
                        repos.append(fpth)
        return repos

