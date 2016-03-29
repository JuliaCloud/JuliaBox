import base64
import shutil
import os
import hashlib
import time
import datetime
import pytz

import isodate
from oauth2client.client import OAuth2Credentials
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI, GOOGLE_AUTH_URI
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


class GDriveSync:
    """Synchronizes folders from Google Drive.

    Requires credentials to be provided as base64 encoded JSON representation of OAuth2Credentials, in form field gauth.

    If credentials are not found, the Google authentication plugin is invoked
    with state as ask_gdrive (/jboxauth/google?state=ask_gdrive). On successful
    authentication and authorization, the plugin must call JuliaBox.init_gauth_tok
    on the browser with appropriately formatted credentials.
    """
    CREDSB64 = None
    CREDS = None
    GAUTH = None
    DRIVE = None
    LOCAL_TZ_OFFSET = 0

    def __init__(self, loc):
        self.loc = loc
        with open(os.path.join(loc, '.gdrive')) as f:
            self.gfolder = f.read().strip()

    def repo_hash(self):
        return hashlib.sha1('_'.join([self.loc, self.gfolder])).hexdigest()

    def repo_name(self):
        return os.path.basename(self.loc) + ' (' + self.gfolder + ')'

    def sync(self):
        self._sync_folder(self.loc, GDriveSync.folder_id(self.gfolder))

    def _sync_folder(self, loc, gfolder):
        # list local folder
        loc_flist = {}
        for f in os.listdir(loc):
            if f.startswith('.'):
                continue
            full_path = os.path.join(loc, f)
            is_dir = os.path.isdir(full_path)
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path), pytz.utc)
            # + datetime.timedelta(seconds=GDriveSync.LOCAL_TZ_OFFSET)
            loc_flist[f] = {'fullpath': full_path, 'is_dir': is_dir, 'mtime': mtime}

        # list remote folder
        gdrive_flist = {}
        for f in GDriveSync.DRIVE.ListFile({'q': "'" + gfolder + "' in parents and trashed=false"}).GetList():
            fname = f['title']
            full_path = os.path.join(loc, fname)
            is_dir = ('application/vnd.google-apps.folder' in f['mimeType'])
            mtime = GDriveSync.parse_gdrive_time(f['modifiedDate'])
            gdrive_flist[fname] = {'fullpath': full_path, 'is_dir': is_dir, 'mtime': mtime, 'id': f['id']}

        parent_spec = [{"kind": "drive#fileLink", "id": gfolder}]
        # for all files in local folder
        for f, attrs in loc_flist.items():
            # if it is a folder
            if attrs['is_dir']:
                # if file not on remote create remote folder, remove file from local list, add to remote list
                if f not in gdrive_flist:
                    gdrive_file = GDriveSync.DRIVE.CreateFile({
                        'title': f,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': parent_spec,
                        'modifiedDate': attrs['mtime']
                    })
                    gdrive_file.Upload()
                    gdrive_flist[f] = {
                        'fullpath': attrs['full_path'],
                        'is_dir': attrs['is_dir'],
                        'mtime': attrs['mtime'],
                        'id': gdrive_file['id']
                    }
                    del loc_flist[f]
            else:  # it is a file
                # if file not on remote, upload local file, remove file from local list
                if f not in gdrive_flist:
                    GDriveSync._upload(attrs['fullpath'], parents=parent_spec)
                    del loc_flist[f]
                else:
                    gf_attrs = gdrive_flist[f]
                    # if file in remote is older, upload local file
                    tdiff = (attrs['mtime'] - gf_attrs['mtime']).total_seconds()
                    # print("existing file tdiff: " + str(tdiff))
                    if tdiff >= 1:
                        GDriveSync._upload(attrs['fullpath'], parents=None, remid=gf_attrs['id'])
                    # if file on remote is newer, download remote file
                    elif tdiff <= -1:
                        GDriveSync._download(attrs['fullpath'], gf_attrs['id'])
                    #else:
                    #    print("already in sync " + attrs['fullpath'])
                    # remove file from both lists
                    del loc_flist[f]
                    del gdrive_flist[f]

        # for files remaining in remote list
        for f, gf_attrs in gdrive_flist.items():
            # create local folder if it does not exist
            fullpath = gf_attrs['fullpath']
            if gf_attrs['is_dir']:
                if not os.path.exists(fullpath):
                    os.makedirs(fullpath)
            # download remote file, remove from remote list
            else:
                GDriveSync._download(fullpath, gf_attrs['id'])
                del gdrive_flist[f]

        # gdrive_flist should only have folders if any
        # for folders remaining in remote list call _sync_folder recursively on them
        for f, gf_attrs in gdrive_flist.items():
            self._sync_folder(gf_attrs['fullpath'], gf_attrs['id'])

    @staticmethod
    def _upload(locpath, parents=None, remid=None):
        fname = os.path.basename(locpath)
        # print("uploading " + fname + " to " + locpath + ", parents: " + str(parents) + ", remid: " + str(remid))
        gdrive_file = GDriveSync.DRIVE.CreateFile({'id': remid}) if (remid is not None) else \
            GDriveSync.DRIVE.CreateFile({'title': fname, 'parents': parents})
        gdrive_file.SetContentFile(locpath)
        gdrive_file.Upload()
        GDriveSync._sync_file_time(locpath, gdrive_file)

    @staticmethod
    def _download(locpath, remid):
        # print("downloading " + locpath + " from " + remid)
        gdrive_file = GDriveSync.DRIVE.CreateFile({'id': remid})
        gdrive_file.GetContentFile(locpath)
        GDriveSync._sync_file_time(locpath, gdrive_file)

    @staticmethod
    def _sync_file_time(locpath, gdrive_file):
        gdrive_file.FetchMetadata()
        mtime = GDriveSync.parse_gdrive_time(gdrive_file['modifiedDate'])
        timestamp = (mtime - datetime.datetime.fromtimestamp(0, pytz.utc)).total_seconds()
        # print("setting file time to " + str(mtime) + " timestamp: " + str(timestamp))
        os.utime(locpath, (timestamp, timestamp))

    @staticmethod
    def parse_gdrive_time(tm):
        if None != tm:
            tm = isodate.parse_datetime(tm)
        return tm

    @staticmethod
    def local_time_offset():
        """Return offset of local zone from GMT"""
        if time.localtime().tm_isdst and time.daylight:
            return time.altzone
        else:
            return time.timezone

    @staticmethod
    def init_creds(credsb64):
        GDriveSync.LOCAL_TZ_OFFSET = GDriveSync.local_time_offset()
        if GDriveSync.CREDSB64 == credsb64:
            return
        creds_json = base64.b64decode(credsb64)
        creds = OAuth2Credentials.from_json(creds_json)
        GDriveSync.CREDS = creds
        GDriveSync.CREDSB64 = credsb64

        gauth = GoogleAuth()
        gauth.settings = {
            'client_config_backend': 'settings',
            'client_config_file': 'client_secrets.json',
            'save_credentials': False,
            'oauth_scope': ['https://www.googleapis.com/auth/drive'],
            'client_config': {
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'auth_uri': GOOGLE_AUTH_URI,
                'token_uri': GOOGLE_TOKEN_URI,
                'revoke_uri': GOOGLE_REVOKE_URI,
                'redirect_uri': 'http://juliabox.org/jboxauth/google/'
            }
        }
        gauth.LoadClientConfigSettings()
        gauth.credentials = creds
        GDriveSync.GAUTH = gauth

        GDriveSync.DRIVE = GoogleDrive(gauth)

    @staticmethod
    def folder_name(gfolder):
        return gfolder.split('/')[-2]

    @staticmethod
    def folder_id(gfolder):
        return gfolder.split('/')[-1]

    @staticmethod
    def clone(gfolder, loc, overwrite=False):
        if overwrite and os.path.exists(loc):
            shutil.rmtree(loc)

        # create the folder and .gdrive file
        if not os.path.exists(loc):
            os.mkdir(loc)

        with open(os.path.join(loc, '.gdrive'), 'w') as f:
            f.write(gfolder)
        GDriveSync._clone_gfolder(GDriveSync.folder_id(gfolder), loc)
        return GDriveSync(loc)

    @staticmethod
    def _clone_gfolder(gfolder, loc):
        drive = GDriveSync.DRIVE
        for f in drive.ListFile({'q': "'" + gfolder + "' in parents and trashed=false"}).GetList():
            fpath = os.path.join(loc, f['title'])
            if 'application/vnd.google-apps.folder' in f['mimeType']:
                os.mkdir(fpath)
                GDriveSync._clone_gfolder(f['id'], fpath)
            else:
                GDriveSync._download(fpath, f['id'])

    @staticmethod
    def scan_repo_paths(dirs):
        repos = []
        for d in dirs:
            for pth in os.listdir(d):
                if pth.startswith('.'):
                    continue
                fpth = os.path.join(d, pth)
                if os.path.isdir(fpth):
                    gdrive_pth = os.path.join(fpth, '.gdrive')
                    if os.path.isfile(gdrive_pth):
                        repos.append(fpth)
        return repos
