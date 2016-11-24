import argparse
import sys
import os
import ipdb
import re
from datetime import datetime


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


class LineParser:
    DATETIME_FORMAT = '%a %b %d %H:%M:%S %Y'
    LINE_RE = re.compile(r"""
        ^\[pid:\s(?P<pid>\d+)\|app:\s(?P<app>\d+)\|req:\s(?P<request_id>\d+\/\d+)\]\s
        (?P<ip>[\d.]+)\s\(.*\)\s
        \{(?P<request_vars>\d+) \svars\sin\s (?P<request_size>\d+)\sbytes\}\s
        \[(?P<datetime>.+?)\]\s
        (?P<request_method>POST|GET|DELETE|PUT|PATCH)\s
        (?P<request_uri>[^ ]*?)\ =>\ generated\ (?:.*?)\ in\ (?P<response_msecs>\d+)\ msecs\s
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
                'request_size': int(raw_data['request_size']),
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


if __name__ == '__main__':
    parsed_args = parse_args(sys.argv[1:])
    ipdb.set_trace()
