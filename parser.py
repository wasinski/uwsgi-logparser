import sys
import re
from datetime import datetime
from collections import defaultdict

from cli import parse_args
from utils import TimeFrame, humanize, dict_to_str


class LineParser:
    DATETIME_FORMAT = '%a %b %d %H:%M:%S %Y'
    LINE_RE = re.compile(r"""
        ^\[pid:\s(?P<pid>\d+)\|app:\ (?P<app>\d+)\|req:\ (?P<request_id>\d+\/\d+)\]\s
        (?P<ip>[\d.]+)\s\(.*\)\s
        \{(?P<request_vars>\d+) \ vars\ in\  (?P<request_size>\d+)\sbytes\}\s
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


class LogParser:

    def __init__(self, lineparser):
        self.lineparser = lineparser

    def parse(self, filename):
        with open(filename, 'r') as f:
            yield from map(self.lineparser.parse, f.readlines())


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
            if not log_entry:
                continue
            if log_entry['datetime'] in self.time_frame:
                first_datetime = first_datetime or log_entry['datetime']
                requests_count += 1
                response_status_count[log_entry['status']] += 1
                if log_entry['status'].startswith('2'):
                    twohoundreds_total_size += log_entry['response_size']
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

    def get_output_stats(self, data=None):
        if not data:
            data = self.analyze()
        requests = data['requests_count']
        time_delta = data['last_datetime'] - data['first_datetime']
        req_per_sec = str(round(requests / time_delta.seconds, 3))
        twohoundreds_avg_size = humanize(data['2XX_total_size'] // data['2XX_count'])
        response_status = dict_to_str(data['response_status_count'])
        return {
            'requests': str(requests),
            'status_count': response_status,
            'request_per_second': req_per_sec,
            '2XX_avg_size': twohoundreds_avg_size,
        }


if __name__ == '__main__':
    parsed_args = parse_args(sys.argv[1:])
    log_parser = LogParser(LineParser)
    parsed_lines = log_parser.parse(parsed_args.filename)
    analyzer = Analyzer(parsed_lines, start=parsed_args.start, end=parsed_args.end)
    try:
        stats = analyzer.get_output_stats()
    except (TypeError, ZeroDivisionError):
        print(('It looks like in given time frame there were made less than two requests.\n'
               'Stats are unavailable.'))
    else:
        message = ('Requests: {requests}\n'
                   'Requests per second: {request_per_second}\n'
                   'Responses: {status_count}\n'
                   'Avg 2XX response size: {2XX_avg_size}\n').format(**stats)
        print(message, end='')
