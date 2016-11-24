import pytest
import tempfile
from datetime import datetime
from io import StringIO
from unittest.mock import patch

from parser import parse_args, LineParser, TimeFrame


@pytest.fixture
def logfile(request):
    return tempfile.mkstemp(text=True)


class CLITests:

    def test_without_filename_arg_show_usage_message(self):
        with patch('sys.stderr', new=StringIO()) as mocked_err:
            with pytest.raises(SystemExit):
                parse_args([])
            assert 'usage:' in mocked_err.getvalue()

    def test_if_file_doesnt_exist_return_error(self):
        with patch('sys.stderr', new=StringIO()) as mocked_err:
            with pytest.raises(SystemExit):
                parse_args(['some-filename-that-certainly-doesnt-exist.log'])
            assert 'usage:' in mocked_err.getvalue()

    def test_accepts_start_timestamp(self, logfile):
        _, filename = logfile
        argparser = parse_args([filename, '--start', '11-11-2011_11-11-11'])
        assert isinstance(argparser.start, datetime)

    def test_accepts_end_timestamp(self, logfile):
        _, filename = logfile
        argparser = parse_args([filename, '--end', '11-11-2011_11-11-11'])
        assert isinstance(argparser.end, datetime)

    def test_end_timestamp_has_to_be_greater_than_start(self, logfile):
        _, filename = logfile
        with patch('sys.stderr', new=StringIO()) as mocked_err:
            with pytest.raises(SystemExit):
                parse_args([filename, '--start', '11-11-2011_11-11-11', '--end', '11-11-2010_11-11-11'])
            assert 'usage:' in mocked_err.getvalue()

    def test_baddly_formatted_timestamp_raise_error(self, logfile):
        _, filename = logfile
        with patch('sys.stderr', new=StringIO()) as mocked_err:
            with pytest.raises(SystemExit):
                parse_args([filename, '--start', '1111-11-11_11-11-11'])
            assert 'usage:' in mocked_err.getvalue()


class LineParserTests:

    def test_proper_log_line(self):
        input_line = ('[pid: 16992|app: 0|req: 164/164] 127.0.0.1 ()'
                     ' {46 vars in 917 bytes} [Mon Nov 21 17:57:20 2016]'
                     ' GET /sonel_core/customeruser/add/ => generated 35830'
                     ' bytes in 632 msecs (HTTP/1.1 200) 7 headers in 373 bytes'
                     ' (1 switches on core 0)')
        expected = {
            'datetime': datetime(2016, 11, 21, 17, 57, 20),
            'request_size': 917,
            'status': '200',
        }

        output = LineParser.parse(input_line)
        assert output == expected

    def test_line_without_a_match(self):
        input_line = 'Traceback (most recent call last):'
        expected = None

        output = LineParser.parse(input_line)
        assert output == expected


class TimeFrameTests:

    @pytest.fixture(scope='class')
    def time_frame(self, request):
        start = datetime(2016, 11, 11, 12, 13, 14)
        end = datetime(2017, 11, 11, 12, 13, 14)
        return TimeFrame(start, end)

    def test_datetime_sooner_than_start(self, time_frame):
        dt = datetime(2015, 11, 11, 12, 13, 14)
        assert dt not in time_frame

    def test_datetime_later_than_end(self, time_frame):
        dt = datetime(2018, 11, 11, 12, 13, 14)
        assert dt not in time_frame

    def test_datetime_is_start(self, time_frame):
        dt = datetime(2016, 11, 11, 12, 13, 14)
        assert dt in time_frame

    def test_datetime_is_end(self, time_frame):
        dt = datetime(2017, 11, 11, 12, 13, 14)
        assert dt in time_frame

    def test_datetime_is_in_between(self, time_frame):
        dt = datetime(2016, 11, 27, 12, 13, 14)
        assert dt in time_frame
