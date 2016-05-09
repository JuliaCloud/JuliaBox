__author__ = 'Nishanth'

import os
import urllib
import io
from juliabox.cloud import JBPluginCloud
from juliabox.jbox_util import JBoxCfg
from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from mimetypes import MimeTypes
from time import sleep
from random import random
import threading

class KeyStruct:
    def __init__(self, **entries): 
        self.__dict__.update(entries)
        self.size = int(self.size)

class JBoxGS(JBPluginCloud):
    provides = [JBPluginCloud.JBP_BUCKETSTORE, JBPluginCloud.JBP_BUCKETSTORE_GS]
    threadlocal = threading.local()
    BUCKETS = dict()
    MAX_RETRIES = 10
    RETRYABLE_ERRORS = [500, 502, 503, 504]
    MAX_BACKOFF = 32
    BACKOFF_FACTOR = 2
    SLEEP_TIME = 3

    @staticmethod
    def configure():
        JBoxGS.MAX_RETRIES = JBoxCfg.get('bucket_gs.max_retries', 10)

    @staticmethod
    def connect():
        c = getattr(JBoxGS.threadlocal, 'conn', None)
        if c is None:
            JBoxGS.configure()
            creds = GoogleCredentials.get_application_default()
            JBoxGS.threadlocal.conn = c = build("storage", "v1",
                                                credentials=creds)
        return c

    @staticmethod
    def connect_bucket(bucket):
        if bucket not in JBoxGS.BUCKETS:
            JBoxGS.BUCKETS[bucket] = JBoxGS.connect().buckets().get(
                bucket=bucket).execute()
        return JBoxGS.BUCKETS[bucket]

    @staticmethod
    def _get_mime_type(local_file):
        mime = MimeTypes()
        url = urllib.pathname2url(local_file)
        mime_type = mime.guess_type(url)
        return mime_type[0]

    @staticmethod
    def push(bucket, local_file, metadata=None):
        objconn = JBoxGS.connect().objects()
        fh = open(local_file, "rb")
        media = MediaIoBaseUpload(fh, JBoxGS._get_mime_type(local_file),
                                  resumable=True, chunksize=4*1024*1024)
        uploader = None
        if metadata:
            uploader = objconn.insert(bucket=bucket, media_body=media,
                                      name=os.path.basename(local_file),
                                      body={"metadata": metadata})
        else:
            uploader = objconn.insert(bucket=bucket, media_body=media,
                                      name=os.path.basename(local_file))
        done = False
        num_retries = 0
        while not done:
            try:
                _, done = uploader.next_chunk()
            except HttpError, err:
                num_retries += 1
                if num_retries > JBoxGS.MAX_RETRIES:
                    fh.close()
                    raise
                if err.resp.status in JBoxGS.RETRYABLE_ERRORS:
                    backoff = min(JBoxGS.BACKOFF_FACTOR ** (num_retries - 1),
                                  JBoxGS.MAX_BACKOFF)
                    sleep(backoff + random())
                else:
                    sleep(JBoxGS.SLEEP_TIME)
            except:
                fh.close()
                raise
        fh.close()

        if not done:
            return None
        return KeyStruct(**done)

    @staticmethod
    def pull(bucket, local_file, metadata_only=False):
        objname = os.path.basename(local_file)
        k = None
        try:
            k = JBoxGS.connect().objects().get(bucket=bucket,
                                               object=objname).execute()
        except HttpError as err:
            if err._get_reason() != 'Not Found':
                raise(err)
            else:
                return None

        if not metadata_only:
            req = JBoxGS.connect().objects().get_media(bucket=bucket,
                                                       object=objname)
            fh = open(local_file, "wb")
            downloader = MediaIoBaseDownload(fh, req, chunksize=4*1024*1024)
            done = False
            num_retries = 0
            while not done:
                try:
                    _, done = downloader.next_chunk()
                except HttpError, err:
                    num_retries += 1
                    if num_retries > JBoxGS.MAX_RETRIES:
                        fh.close()
                        os.remove(local_file)
                        raise
                    if err.resp.status in JBoxGS.RETRYABLE_ERRORS:
                        backoff = min(JBoxGS.BACKOFF_FACTOR ** (num_retries - 1),
                                      JBoxGS.MAX_BACKOFF)
                        sleep(backoff + random())
                    else:
                        sleep(JBoxGS.SLEEP_TIME)
                except:
                    fh.close()
                    os.remove(local_file)
                    raise
            fh.close()

        if k is None:
            return None
        return KeyStruct(**k)

    @staticmethod
    @retry_on_errors(retries=2)
    def _delete(bucket, key_name):
        return JBoxGS.connect().objects().delete(bucket=bucket,
                                                 object=key_name).execute()

    @staticmethod
    def delete(bucket, local_file):
        key_name = os.path.basename(local_file)
        k = JBoxGS._delete(bucket, key_name)
        if k is None:
            return None
        return KeyStruct(**k)

    @staticmethod
    @retry_on_errors(retries=2)
    def _copy(from_bucket, from_key_name, to_bucket, to_key_name):
        return JBoxGS.connect().objects().copy(sourceBucket=from_bucket,
                                               sourceObject=from_key_name,
                                               destinationBucket=to_bucket,
                                               destinationObject=to_key_name,
                                               body={}).execute()

    @staticmethod
    def copy(from_file, to_file, from_bucket, to_bucket=None):
        if to_bucket is None:
            to_bucket = from_bucket

        from_key_name = os.path.basename(from_file)
        to_key_name = os.path.basename(to_file)

        k = JBoxGS._copy(from_bucket, from_key_name, to_bucket, to_key_name)
        if k is None:
            return None
        return KeyStruct(**k)

    @staticmethod
    def move(from_file, to_file, from_bucket, to_bucket=None):
        k_new = JBoxGS.copy(from_file, to_file, from_bucket, to_bucket)
        if k_new is None:
            return None
        JBoxGS.delete(from_bucket, from_file)
        return k_new
