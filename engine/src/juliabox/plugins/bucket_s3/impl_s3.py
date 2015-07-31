__author__ = 'tan'

import os
import boto
from boto.s3.key import Key

from juliabox.cloud import JBoxCloudPlugin


class JBoxS3(JBoxCloudPlugin):
    provides = [JBoxCloudPlugin.PLUGIN_BUCKETSTORE, JBoxCloudPlugin.PLUGIN_BUCKETSTORE_S3]
    CONN = None
    BUCKETS = dict()

    @staticmethod
    def connect():
        if JBoxS3.CONN is None:
            JBoxS3.CONN = boto.connect_s3()
        return JBoxS3.CONN

    @staticmethod
    def connect_bucket(bucket):
        if bucket not in JBoxS3.BUCKETS:
            JBoxS3.BUCKETS[bucket] = JBoxS3.connect().get_bucket(bucket)
        return JBoxS3.BUCKETS[bucket]

    @staticmethod
    def push(bucket, local_file, metadata=None):
        key_name = os.path.basename(local_file)
        k = Key(JBoxS3.connect_bucket(bucket))
        k.key = key_name
        if metadata is not None:
            for meta_name, meta_value in metadata.iteritems():
                k.set_metadata(meta_name, meta_value)
        k.set_contents_from_filename(local_file)
        return k

    @staticmethod
    def pull(bucket, local_file, metadata_only=False):
        key_name = os.path.basename(local_file)
        k = JBoxS3.connect_bucket(bucket).get_key(key_name)
        if (k is not None) and (not metadata_only):
            k.get_contents_to_filename(local_file)
        return k

    @staticmethod
    def delete(bucket, local_file):
        key_name = os.path.basename(local_file)
        k = JBoxS3.connect_bucket(bucket).delete_key(key_name)
        return k

    @staticmethod
    def copy(from_file, to_file, from_bucket, to_bucket=None):
        if to_bucket is None:
            to_bucket = from_bucket

        from_key_name = os.path.basename(from_file)
        to_key_name = os.path.basename(to_file)

        k = JBoxS3.connect_bucket(from_bucket).get_key(from_key_name)
        if k is None:
            return None
        k_new = k.copy(to_bucket, to_key_name)
        return k_new

    @staticmethod
    def move(from_file, to_file, from_bucket, to_bucket=None):
        k_new = JBoxS3.copy(from_file, to_file, from_bucket, to_bucket)
        if k_new is None:
            return None
        JBoxS3.delete(from_bucket, from_file)
        return k_new