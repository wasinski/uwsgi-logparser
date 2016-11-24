import pytest
import tempfile
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

from parser import parse_args, LineParser, TimeFrame, Analyzer


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
            'response_size': 35830,
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


class AnalyzerTests:

    ENTRY_1_DATETIME = datetime(2016, 11, 27, 12, 13, 14)
    ENTRY_2_DATETIME = datetime(2016, 11, 27, 12, 13, 16)
    ENTRY_3_DATETIME = datetime(2016, 11, 27, 12, 13, 19)

    @pytest.fixture(scope='class')
    def entry_1(self):
        return {
            'datetime': self.ENTRY_1_DATETIME,
            'request_size': 128,
            'status': '200',
        }

    @pytest.fixture(scope='class')
    def entry_2(self):
        return {
            'datetime': self.ENTRY_2_DATETIME,
            'request_size': 128,
            'status': '200',
        }

    @pytest.fixture(scope='class')
    def entry_3(self):
        return {
            'datetime': self.ENTRY_3_DATETIME,
            'request_size': 256,
            'status': '301',
        }

    def test_no_entry_given(self):
        data = iter([])
        analyzer = Analyzer(data)
        output = analyzer.analyze()
        expected = {
            'requests_count': 0,
            '2XX_total_size': 0,
            'response_status_count': {},
            'first_datetime': None,
            'last_datetime': None,
        }
        assert output == expected

    def test_just_one_entry_given(self, entry_1):
        data = iter([entry_1])
        analyzer = Analyzer(data)
        output = analyzer.analyze()
        expected = {
            'requests_count': 1,
            '2XX_total_size': 128,
            'response_status_count': {'200': 1},
            'first_datetime': self.ENTRY_1_DATETIME,
            'last_datetime': self.ENTRY_1_DATETIME,
        }
        assert output == expected

    def test_two_entries_given(self, entry_1, entry_2):
        data = iter([entry_1, entry_2])
        analyzer = Analyzer(data)
        output = analyzer.analyze()
        expected = {
            'requests_count': 2,
            '2XX_total_size': 256,
            'response_status_count': {'200': 2},
            'first_datetime': self.ENTRY_1_DATETIME,
            'last_datetime': self.ENTRY_2_DATETIME,
        }
        assert output == expected

    def test_three_entries_given(self, entry_1, entry_2, entry_3):
        data = iter([entry_1, entry_2, entry_3])
        analyzer = Analyzer(data)
        output = analyzer.analyze()
        expected = {
            'requests_count': 3,
            '2XX_total_size': 256,
            'response_status_count': {'200': 2, '301': 1},
            'first_datetime': self.ENTRY_1_DATETIME,
            'last_datetime': self.ENTRY_3_DATETIME,
        }
        assert output == expected

    def test_entries_not_in_given_timeframe(self, entry_1, entry_2, entry_3):
        data = iter([entry_1, entry_2, entry_3])
        analyzer = Analyzer(data, end=datetime(2016, 11, 27, 12, 13, 10))
        output = analyzer.analyze()
        expected = {
            'requests_count': 0,
            '2XX_total_size': 0,
            'response_status_count': {},
            'first_datetime': None,
            'last_datetime': None,
        }
        assert output == expected
