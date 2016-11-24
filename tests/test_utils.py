import pytest
from datetime import datetime

from ..utils import TimeFrame


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
