import pytest
import tempfile
from datetime import datetime
from io import StringIO
from unittest.mock import patch

from ..cli import parse_args


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
