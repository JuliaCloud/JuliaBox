__author__ = 'Nishanth'

import threading
import datetime
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from juliabox.cloud import JBPluginCloud
from oauth2client.client import GoogleCredentials

from juliabox.jbox_util import JBoxCfg, retry_on_errors

class GoogleMonitoringV3(JBPluginCloud):
    provides = [JBPluginCloud.JBP_MONITORING,
                JBPluginCloud.JBP_MONITORING_GOOGLE,
                JBPluginCloud.JBP_MONITORING_GOOGLE_V3]
    threadlocal = threading.local()

    RFC_3339_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    ALLOWED_CUSTOM_GCE_VALUE_TYPES = ['DOUBLE', 'INT64']
    ALLOWED_EC2_VALUE_TYPES = ['Percent', 'Count']
    CUSTOM_METRIC_DOMAIN = 'custom.googleapis.com/'
    SELF_STATS = dict()

    @staticmethod
    def _connect_google_monitoring():
        c = getattr(GoogleMonitoringV3.threadlocal, 'cm_conn', None)
        if c is None:
            creds = GoogleCredentials.get_application_default()
            GoogleMonitoringV3.threadlocal.cm_conn = c = build('monitoring', 'v3',
                                                               credentials=creds).projects()
        return c

    @staticmethod
    def _get_google_now():
        return datetime.datetime.utcnow().strftime(GoogleMonitoringV3.RFC_3339_FORMAT)

    @staticmethod
    def _process_value_type(value_type):
        if value_type in GoogleMonitoringV3.ALLOWED_EC2_VALUE_TYPES:
            if value_type == 'Count':
                return 'INT64'
            return 'DOUBLE'
        elif value_type in GoogleMonitoringV3.ALLOWED_CUSTOM_GCE_VALUE_TYPES:
            return value_type
        else:
            raise Exception('Invalid value_type argument.')

    @staticmethod
    def _get_timeseries_dict(metric_name, labels, value, value_type, timenow, instance_id, zone):
        value_type = GoogleMonitoringV3._process_value_type(value_type)
        if value_type == 'DOUBLE':
            value = value / 100
        timeseries = {
            'metric': {
                'type': GoogleMonitoringV3.CUSTOM_METRIC_DOMAIN + metric_name,
                'labels': labels,
            },
            'resource': {
                'type': 'gce_instance',
                'labels': {
                    'instance_id': instance_id,
                    'zone': zone,
                },
            },
            'points': [
                {
                    'interval': {
                        'endTime': timenow,
                    },
                    'value': {
                        value_type.lower() + 'Value': value
                    }
                },
            ],
        }
        return timeseries

    @staticmethod
    @retry_on_errors(retries=2)
    def _ts_write(timeseries, install_id):
        ts = GoogleMonitoringV3._connect_google_monitoring().timeSeries()
        return ts.create(name='projects/' + install_id,
                         body={'timeSeries': timeseries}).execute()

    @staticmethod
    def _update_timeseries(timeseries):
        timenow = GoogleMonitoringV3._get_google_now()
        for ts in timeseries:
            ts['points'][0]['interval']['endTime'] = timenow

    @staticmethod
    def _timeseries_write(timeseries, install_id):
        try:
            GoogleMonitoringV3._ts_write(timeseries, install_id)
        except HttpError, err:
            if err.resp.status == 400:
                time.sleep(1)
                GoogleMonitoringV3._update_timeseries(timeseries)
                GoogleMonitoringV3._ts_write(timeseries, install_id)
            else:
                raise

    @staticmethod
    def publish_stats_multi(stats, instance_id, this_id, install_id,
                            autoscale_group, zone):
        timeseries = []
        label = {'InstanceID': instance_id, 'GroupID': autoscale_group}
        timenow = GoogleMonitoringV3._get_google_now()
        should_cache = this_id == instance_id
        for (stat_name, stat_unit, stat_value) in stats:
            if should_cache:
                GoogleMonitoringV3.SELF_STATS[stat_name] = stat_value
            GoogleMonitoringV3.log_info('CloudMonitoring %s.%s.%s=%r(%s)',
                                        install_id, instance_id, stat_name,
                                        stat_value, stat_unit)
            timeseries.append(
                GoogleMonitoringV3._get_timeseries_dict(stat_name, label,
                                                        stat_value, stat_unit,
                                                        timenow, instance_id,
                                                        zone))
        GoogleMonitoringV3._timeseries_write(timeseries, install_id)

    @staticmethod
    def _list_metric(project, metric_name, instance_id, group_id):
        ts = GoogleMonitoringV3._connect_google_monitoring().timeSeries()
        nowtime = datetime.datetime.utcnow()
        retlist = []
        nextpage = None
        # labels = [GoogleMonitoringV3.CUSTOM_METRIC_DOMAIN + label for label in labels]
        filter = 'metric.type = "' + GoogleMonitoringV3.CUSTOM_METRIC_DOMAIN \
                 + metric_name + '"\nmetric.label.InstanceID = "' + \
                 instance_id +'"\nmetric.label.GroupID = "' + group_id + '"'
        while True:
            start = time.time()
            resp = None
            while True:
                try:
                    resp = ts.list(name='projects/' + project, filter=filter,
                                   interval_startTime=(nowtime - datetime.timedelta(minutes=30)).strftime(GoogleMonitoringV3.RFC_3339_FORMAT),
                                   interval_endTime=nowtime.strftime(GoogleMonitoringV3.RFC_3339_FORMAT),
                                   aggregation_alignmentPeriod='60s',
                                   aggregation_perSeriesAligner='ALIGN_MEAN',
                                   pageToken=nextpage).execute()
                    break
                except:
                    if time.time() < start + 20:
                        time.sleep(3)
                    else:
                        raise
            series = resp.get('timeSeries')
            if series == None:
                break
            retlist.extend(series[0]['points'])
            nextpage = resp.get('nextPageToken')
            if nextpage == None:
                break
        return retlist

    @staticmethod
    def get_instance_stats(instance, stat_name, this_id, install_id,
                           autoscale_group):
        if (instance == this_id) and (stat_name in GoogleMonitoringV3.SELF_STATS):
            GoogleMonitoringV3.log_debug('Using cached self_stats. %s=%r',
                                         stat_name, GoogleMonitoringV3.SELF_STATS[stat_name])
            return GoogleMonitoringV3.SELF_STATS[stat_name]
        res = None
        results = GoogleMonitoringV3._list_metric(project=install_id,
                                                  metric_name=stat_name,
                                                  instance_id=instance,
                                                  group_id=autoscale_group)
        for _res in results:
            if (res is None) or (res['interval']['endTime'] < _res['interval']['endTime']):
                res = _res
        if res:
            return res['value'].values()[0]
        return None

    @staticmethod
    def get_metric_dimensions(metric_name, install_id, autoscale_group):
        next_token = None
        dims = {}
        ts = GoogleMonitoringV3._connect_google_monitoring().timeSeries()
        nowtime = datetime.datetime.utcnow()
        filter = 'metric.type = "' + GoogleMonitoringV3.CUSTOM_METRIC_DOMAIN \
                 + metric_name + '"\nmetric.label.GroupID = "' + autoscale_group + '"'
        while True:
            start = time.time()
            metrics = None
            while True:
                try:
                    metrics = ts.list(pageToken=next_token, filter=filter,
                                      name='projects/' + install_id,
                                      interval_startTime=(nowtime - datetime.timedelta(minutes=30)).strftime(GoogleMonitoringV3.RFC_3339_FORMAT),
                                      interval_endTime=nowtime.strftime(GoogleMonitoringV3.RFC_3339_FORMAT),
                                      view='HEADERS').execute()
                    break
                except:
                    if time.time() < start + 20:
                        time.sleep(3)
                    else:
                        raise
            series = metrics.get('timeSeries')
            if series == None:
                break
            for m in series:
                for n_dim, v_dim in m['metric']['labels'].iteritems():
                    dims[n_dim] = dims.get(n_dim, []) + [v_dim]
            next_token = metrics.get('nextPageToken')
            if next_token is None:
                break
        if len(dims) == 0:
            GoogleMonitoringV3.log_warn('invalid metric ' + '.'.join([install_id, metric_name]))
            return None
        return dims
