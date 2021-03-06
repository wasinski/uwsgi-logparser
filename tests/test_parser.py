import pytest
import tempfile
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

from ..parser import parse_args, LineParser, Analyzer, dict_to_str


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


class AnalyzerAnalyzeTests:

    ENTRY_1_DATETIME = datetime(2016, 11, 27, 12, 13, 14)
    ENTRY_2_DATETIME = datetime(2016, 11, 27, 12, 13, 16)
    ENTRY_3_DATETIME = datetime(2016, 11, 27, 12, 13, 19)

    @pytest.fixture(scope='class')
    def entry_1(self):
        return {
            'datetime': self.ENTRY_1_DATETIME,
            'response_size': 128,
            'status': '200',
        }

    @pytest.fixture(scope='class')
    def entry_2(self):
        return {
            'datetime': self.ENTRY_2_DATETIME,
            'response_size': 128,
            'status': '200',
        }

    @pytest.fixture(scope='class')
    def entry_3(self):
        return {
            'datetime': self.ENTRY_3_DATETIME,
            'response_size': 256,
            'status': '301',
        }

    def test_no_entry_given(self):
        data = iter([])
        analyzer = Analyzer(data)
        output = analyzer.analyze()
        expected = {
            'requests_count': 0,
            '2XX_total_size': 0,
            '2XX_count': 0,
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
            '2XX_count': 1,
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
            '2XX_count': 2,
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
            '2XX_count': 2,
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
            '2XX_count': 0,
            'response_status_count': {},
            'first_datetime': None,
            'last_datetime': None,
        }
        assert output == expected


class AnalyzerGetOutputStatsTests:

    def test_no_data(self):
        analyzer = Analyzer([])
        with pytest.raises(TypeError):
            analyzer.get_output_stats({})

    def test_data_from_one_request(self):
        STATUS_DICT = {'201': 1}
        data = {
            'requests_count': 1,
            '2XX_total_size': 2048,
            '2XX_count': 1,
            'response_status_count': STATUS_DICT,
            'first_datetime': datetime(2016, 11, 11, 11, 11, 11),
            'last_datetime': datetime(2016, 11, 11, 11, 11, 11),
        }
        analyzer = Analyzer([])
        with pytest.raises(ZeroDivisionError):
            analyzer.get_output_stats(data)

    def test_data_from_two_requests(self):
        STATUS_DICT = {'200': 1, '201': 1}
        data = {
            'requests_count': 2,
            '2XX_total_size': 2048,
            '2XX_count': 2,
            'response_status_count': STATUS_DICT,
            'first_datetime': datetime(2016, 11, 11, 11, 11, 11),
            'last_datetime': datetime(2016, 11, 11, 11, 11, 12),
        }
        expected = {
            'requests': '2',
            'status_count': dict_to_str(STATUS_DICT),
            'request_per_second': '2.0',
            '2XX_avg_size': '1 KB',
        }
        analyzer = Analyzer([])
        out = analyzer.get_output_stats(data)
        assert out == expected

    def test_data_from_three_requests(self):
        STATUS_DICT = {'200': 2, '201': 1}
        data = {
            'requests_count': 3,
            '2XX_total_size': 2048+512,
            '2XX_count': 3,
            'response_status_count': STATUS_DICT,
            'first_datetime': datetime(2016, 11, 11, 11, 11, 11),
            'last_datetime': datetime(2016, 11, 11, 11, 11, 14),
        }
        expected = {
            'requests': '3',
            'status_count': dict_to_str(STATUS_DICT),
            'request_per_second': '1.0',
            '2XX_avg_size': '853 B',
        }
        analyzer = Analyzer([])
        out = analyzer.get_output_stats(data)
        assert out == expected

    def test_data_from_four_requests(self):
        STATUS_DICT = {'200': 2, '201': 1, '400': 1}
        data = {
            'requests_count': 4,
            '2XX_total_size': 2048+512,
            '2XX_count': 3,
            'response_status_count': STATUS_DICT,
            'first_datetime': datetime(2016, 11, 11, 11, 11, 11),
            'last_datetime': datetime(2016, 11, 11, 11, 11, 14),
        }
        expected = {
            'requests': '4',
            'status_count': dict_to_str(STATUS_DICT),
            'request_per_second': '1.333',
            '2XX_avg_size': '853 B',
        }
        analyzer = Analyzer([])
        out = analyzer.get_output_stats(data)
        assert out == expected
