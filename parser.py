import argparse
import sys
import os
import ipdb
import re
from datetime import datetime, timedelta
from collections import defaultdict


def valid_datetime(timestamp):
    DATETIME_FORMAT = '%d-%m-%Y_%H-%M-%S'
    try:
        return datetime.strptime(timestamp, DATETIME_FORMAT)
    except ValueError:
        msg = "Given timestamp doesn't match expected format': '{0}'.".format(timestamp)
        raise argparse.ArgumentTypeError(msg)


def valid_file(filename):
    if os.path.isfile(filename):
        return filename
    else:
        msg = "File doesn't exist, or isn't a file': '{0}'.".format(filename)
        raise argparse.ArgumentTypeError(msg)


def parse_args(args):
    parser = argparse.ArgumentParser(description='uWSGI log parser, returns some basic stats for given time frame')
    parser.add_argument('filename', type=valid_file, help='path to a valid uWSGI log file')
    parser.add_argument('--start', type=valid_datetime, help='format: DD-MM-YYYY_HH-MM-SS')
    parser.add_argument('--end', type=valid_datetime, help='format: DD-MM-YYYY_HH-MM-SS')
    parser_args = parser.parse_args(args)
    if parser_args.start and parser_args.end:
        if parser_args.start >= parser_args.end:
            parser.error('End argument should be greater than start')
    return parser_args


def humanize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0:
        return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


class LineParser:
    DATETIME_FORMAT = '%a %b %d %H:%M:%S %Y'
    LINE_RE = re.compile(r"""
        ^\[pid:\s(?P<pid>\d+)\|app:\s(?P<app>\d+)\|req:\s(?P<request_id>\d+\/\d+)\]\s
        (?P<ip>[\d.]+)\s\(.*\)\s
        \{(?P<request_vars>\d+) \svars\sin\s (?P<request_size>\d+)\sbytes\}\s
        \[(?P<datetime>.+?)\]\s
        (?P<request_method>POST|GET|DELETE|PUT|PATCH)\s
        (?P<request_uri>[^ ]*?)\ =>\ generated\ (?P<response_size>\d+)\ bytes\ in\ (?P<response_msecs>\d+)\ msecs\s
        \(HTTP/[\d.]+\ (?P<response_status>\d+)\)
        """, re.VERBOSE)

    @classmethod
    def parse(cls, line):
        match = cls.LINE_RE.search(line)
        if match:
            raw_data = match.groupdict()
            return {
                'datetime': datetime.strptime(raw_data['datetime'], cls.DATETIME_FORMAT),
                'status': raw_data['response_status'],
                'response_size': int(raw_data['response_size']),
            }


class TimeFrame:

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __contains__(self, datetime):
        in_time_frame = True
        if self.start and datetime < self.start:
            in_time_frame = False
        if self.end and datetime > self.end:
            in_time_frame = False
        return in_time_frame


class Analyzer:

    def __init__(self, parsed_data, start=None, end=None):
        self.data = parsed_data
        self.time_frame = TimeFrame(start, end)

    def analyze(self):
        first_datetime, last_datetime = None, None
        requests_count = 0
        twohoundreds_total_size, twohoundreds_count = 0, 0
        response_status_count = defaultdict(int)
        for log_entry in self.data:
            if log_entry['datetime'] in self.time_frame:
                first_datetime = first_datetime or log_entry['datetime']
                requests_count += 1
                response_status_count[log_entry['status']] += 1
                if log_entry['status'].startswith('2'):
                    twohoundreds_total_size += log_entry['request_size']
                    twohoundreds_count += 1
                last_datetime = log_entry['datetime']
        return {
            'requests_count': requests_count,
            '2XX_total_size': twohoundreds_total_size,
            '2XX_count': twohoundreds_count,
            'response_status_count': response_status_count,
            'first_datetime': first_datetime,
            'last_datetime': last_datetime,
        }

    def get_timedelta(self, start, end):
        if start and end:
            return end - start
        else:
            return timedelta(0)

    def get_output_stats(self, data=None):
        if not data:
            data = self.analyze()
        msg = ''
        requests = data['requests_count']
        if requests < 2:
            msg = ('In given time frame there were less than two requests made. '
                   'Not every stat is available.')
            req_per_sec = 'Not available'
        else:
            timedelta = data['last_datetime'] - data['first_datetime']
            req_per_sec = str(round(requests / timedelta.seconds, 3))
        response_status = str(data['response_status_count'])
        twohoundreds_avg_size = humanize(data['2XX_total_size'] // data['2XX_count'])
        return {
            'msg': msg,
            'requests': str(requests),
            'status_count': response_status,
            'request_per_second': req_per_sec,
            '2XX_avg_size': twohoundreds_avg_size,
        }


if __name__ == '__main__':
    parsed_args = parse_args(sys.argv[1:])
    ipdb.set_trace()
