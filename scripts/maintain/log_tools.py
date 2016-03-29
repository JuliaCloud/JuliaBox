#! /usr/bin/env python

__author__ = 'tan'
import sys
import time
import re
from datetime import datetime, timedelta
import boto
import boto.ec2
import boto.ec2.autoscale
import boto.logs

AWS_REGION = 'us-east-1'
CONN_EC2 = None
CONN_LOGS = None


def error_exit(msg):
    print(msg)
    exit()


def conn_ec2():
    global CONN_EC2
    if CONN_EC2 is None:
        print("Connecting to ec2...")
        CONN_EC2 = boto.ec2.connect_to_region(AWS_REGION)
    return CONN_EC2


def conn_logs():
    global CONN_LOGS
    if CONN_LOGS is None:
        print("Connecting to cloudwatch logs...")
        CONN_LOGS = boto.logs.connect_to_region(AWS_REGION)
    return CONN_LOGS


def sanitize_pfx(name_pfx):
    if name_pfx is not None:
        name_pfx = name_pfx.strip()
        if len(name_pfx) == 0:
            name_pfx = None
    return name_pfx


datetime_begin = lambda: datetime.now().replace(year=2014)
datetime_from_ms = lambda ms: datetime.utcfromtimestamp(ms//1000).replace(microsecond=ms%1000*1000)
ms_from_datetime = lambda dt: time.mktime(dt.timetuple()) * 1000
current_milli_time = lambda: int(round(time.time() * 1000))
hours_to_milli = lambda hr: int(hr)*60*60*1000


def get_log_groups(name_pfx=None):
    name_pfx = sanitize_pfx(name_pfx)
    next_token = None
    groups = []
    while True:
        result = conn_logs().describe_log_groups(log_group_name_prefix=name_pfx, next_token=next_token)
        if 'logGroups' in result:
            for group in result['logGroups']:
                groups.append(group)
        if 'nextToken' in result:
            next_token = result['nextToken']
        else:
            break
    return groups


def show_log_groups(name_pfx=None):
    for group in get_log_groups(name_pfx=name_pfx):
        print("%s (%d bytes)" % (group['logGroupName'], group['storedBytes']))


def get_log_streams(group_name, name_pfx=None, show_empty=False,
                    time_from=datetime_begin(),
                    time_till=datetime_from_ms(current_milli_time())):
    name_pfx = sanitize_pfx(name_pfx)
    next_token = None
    filtered_streams = []
    while True:
        result = conn_logs().describe_log_streams(group_name, log_stream_name_prefix=name_pfx, next_token=next_token)
        if 'logStreams' in result:
            streams = result['logStreams']
            for stream in streams:
                first_time = datetime_from_ms(stream['firstEventTimestamp'])
                last_time = datetime_from_ms(stream['lastEventTimestamp'])

                select = True

                if not show_empty and select and stream['storedBytes'] == 0:
                    select = False

                if select:
                    select = (time_from <= first_time <= time_till) or\
                             (time_from <= last_time <= time_till)

                if select:
                    filtered_streams.append(stream)
        if 'nextToken' in result:
            next_token = result['nextToken']
        else:
            break
    return filtered_streams


def filter_event_message(events, filter_string):
    for event in events:
        msg = event['message']
        ts = event['timestamp']
        if (filter_string is None) or (re.search(filter_string, msg) is not None):
            yield (ts, msg)


def filter_log_events(group_name, stream_name, outfile, filter_string=None,
                      time_from=datetime_begin(),
                      time_till=datetime_from_ms(current_milli_time())):
    next_token = None
    time_from = ms_from_datetime(time_from)
    time_till = ms_from_datetime(time_till)
    ntotal = 0
    while True:
        result = conn_logs().get_log_events(group_name, stream_name, start_time=time_from, end_time=time_till,
                                            next_token=next_token)
        events = result['events'] if 'events' in result else []
        if len(events) == 0:
            if ntotal == 0:
                print("\tno events in time range")
            break

        nfiltered = 0
        for (ts, msg) in filter_event_message(events, filter_string):
            outfile.write("%s - %s - %s - %s\n" % (datetime_from_ms(ts).isoformat(), stream_name, group_name, msg))
            nfiltered += 1
        ntotal += nfiltered

        print("\twrote %d/%d events" % (nfiltered, len(events)))

        if 'nextForwardToken' in result:
            next_token = result['nextForwardToken']
        else:
            break
    return ntotal


def show_log_streams(group_name, name_pfx=None, show_empty=False,
                     time_from=datetime_begin(),
                     time_till=datetime_from_ms(current_milli_time())):
    filtered_streams = get_log_streams(group_name, name_pfx, show_empty, time_from, time_till)
    if len(filtered_streams) == 0:
        return

    print("Streams in group %s:" % (group_name,))
    for stream in filtered_streams:
        first_time = datetime_from_ms(stream['firstEventTimestamp'])
        last_time = datetime_from_ms(stream['lastEventTimestamp'])
        print("\t%s (%r to %r, %d bytes)" % (stream['logStreamName'],
                                             first_time.isoformat(), last_time.isoformat(),
                                             stream['storedBytes']))


def download_logs(group_name, outfile, filter_string=None,
                  time_from=datetime_begin(),
                  time_till=datetime_from_ms(current_milli_time())):
    filtered_streams = get_log_streams(group_name, None, False, time_from, time_till)
    ntotal = 0
    for stream in filtered_streams:
        stream_name = stream['logStreamName']
        print("processing stream %s" % (stream_name,))
        ntotal += filter_log_events(group_name, stream_name, outfile, filter_string=filter_string,
                                    time_from=time_from, time_till=time_till)
    print("total %d events written"%(ntotal,))


def process_show_streams(argv):
    grp_match = argv[2]
    if len(argv) > 3:
        time_from = datetime_from_ms(current_milli_time() - hours_to_milli(argv[3]))
        if len(argv) > 4:
            time_till = time_from + timedelta(hours=int(argv[4]))
        else:
            time_till = datetime.now()
    else:
        time_from = datetime_begin()
        time_till = datetime_from_ms(current_milli_time())

    if '*' not in grp_match:
        groups = [grp_match]
    else:
        groups = [group['logGroupName'] for group in get_log_groups(name_pfx=grp_match.split('*')[0])]

    for group in groups:
        show_log_streams(group, time_from=time_from, time_till=time_till)


def process_download(argv):
    grp_match = argv[2]
    outfilename = argv[3]
    filter_string = None
    if len(argv) > 4:
        time_from = datetime_from_ms(current_milli_time() - hours_to_milli(argv[4]))
        if len(argv) > 5:
            time_till = time_from + timedelta(hours=int(argv[5]))
            if len(argv) > 6:
                filter_string = argv[6]
        else:
            time_till = datetime.now()
    else:
        time_from = datetime_begin()
        time_till = datetime_from_ms(current_milli_time())

    if '*' not in grp_match:
        groups = [grp_match]
    else:
        groups = [group['logGroupName'] for group in get_log_groups(name_pfx=grp_match.split('*')[0])]

    with open(outfilename, 'w') as outfile:
        for group in groups:
            print("processing group %s" % (group,))
            download_logs(group, outfile, filter_string=filter_string, time_from=time_from, time_till=time_till)


def process_args(argv):
    if len(argv) < 3:
        print("Usage:")
        print("\t%s <groups> <prefix>" % (argv[0],))
        print("\t%s <streams> <group> [hours_since] [hours]" % (argv[0],))
        print("\t%s <download> <group> <outfile> [hours_since] [hours] [filter(regex)]" % (argv[0],))
        exit(1)
    cmd = argv[1]
    if cmd == 'groups':
        pfx = argv[2]
        show_log_groups(pfx)
    elif cmd == 'streams':
        process_show_streams(argv)
    elif cmd == 'download':
        process_download(argv)

    print("Done")


if __name__ == "__main__":
    process_args(sys.argv)
