#!/usr/bin/python
 
import tornado.ioloop
import tornado.web
import os, time, sys

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

 
cfg = read_config()
 
if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/file-upload", UploadHandler),
        (r"/ping", PingHandler),
        (r"/", BrowseHandler)
    ])
    application.listen(cfg['port'])
    tornado.ioloop.IOLoop.instance().start()

