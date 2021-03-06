import argparse
import os
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
