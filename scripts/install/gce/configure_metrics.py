#!/usr/bin/python

import httplib
from sys import argv
from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials

if len(argv) != 2:
    print("Usage: ./configure_metrics <install-id>")
    exit(-1)

INSTALL_ID = argv[2]
CUSTOM_METRIC_DOMAIN = "custom.cloudmonitoring.googleapis.com/"
ALLOWED_CUSTOM_GCE_VALUE_TYPES = ["double", "int64"]
ALLOWED_EC2_VALUE_TYPES = ["Percent", "Count"]

def retry_on_bsl(f):
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except httplib.BadStatusLine as bsl:
            return f(*args, **kwargs)
    return func

def _process_value_type(value_type):
    if value_type in ALLOWED_EC2_VALUE_TYPES:
        if value_type == "Count":
            return "int64"
        return "double"
    elif value_type in ALLOWED_CUSTOM_GCE_VALUE_TYPES:
        return value_type
    else:
        raise Exception("Invalid value_type argument.")

def _connect_google_monitoring():
    return build("cloudmonitoring", "v2beta2",
                 credentials=GoogleCredentials.get_application_default())

@retry_on_bsl
def _create_metric_descriptor(metric_name, value_type, label_descriptors,
                              metric_desc=""):
    value_type = _process_value_type(value_type)
    body = {
        "name": CUSTOM_METRIC_DOMAIN + metric_name,
        "typeDescriptor": {
            "metricType": "gauge",
            "valueType": value_type,
        },
        "labels": label_descriptors,
        "description": metric_desc
    }
    md = _connect_google_monitoring().metricDescriptors()
    return md.create(project=INSTALL_ID, body=body).execute()

def _configure_metrics():
    metrics = [("NumActiveContainers", "int64"),
               ("NumActiveAPIContainers", "int64"),
               ("CPUUsed", "double"), ("MemUsed", "double"),
               ("DiskUsed", "double"), ("ContainersUsed", "double"),
               ("APIContainersUsed", "double"), ("DiskIdsUsed", "double"),
               ("Load", "double")]
    label_desc = [{"key": CUSTOM_METRIC_DOMAIN + "InstanceID",
                   "description": "The Instance ID"}]
    op = []
    for (name, typ) in metrics:
        op.append(_create_metric_descriptor(name, typ, label_desc))
        print("Configured " + name)
    return op

if __name__ == '__main__':
    print("Configuring metric descriptors...")
    configure_metrics()
    print("Done.")




