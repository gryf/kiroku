#!/usr/bin/env python3
"""
Tests for tzinfo naive implementation
TODO: Make this module pytz[1] compatible

[1] http://pytz.sourceforge.net/
"""

from datetime import datetime, timedelta, tzinfo
import unittest

from kiroku import naive_tzinfo


class CommonMock:
    """Container"""
    pass


class MockPytzTimezone(tzinfo):
    """Mock pytz module for Europe/Berlin"""

    def tzname(self, dt_arg):
        """tzinfo.tzname implementation"""
        return "CEST"

    def dst(self, dt_arg):
        """tzinfo.dst implementation"""
        return timedelta(hours=2)

    def utcoffset(self, dt_arg):
        """tzinfo.utcoffset implementation"""
        return timedelta(hours=2)

    def localize(self, dt_arg):
        """return datetime from the argument updated with the timezone info"""
        return dt_arg.replace(tzinfo=self)


class TestUTCTimeZone(unittest.TestCase):
    """UTC tzinfo class tests"""

    def setUp(self):
        """Setup"""
        self.dates = ('2013-01-01 01:59:59', '2013-04-01 02:00:00',
                      '2013-06-01 01:59:59', '2013-09-01 02:00:00')

    def test_utcoffset(self):
        """Tests of utf offsets"""
        for str_ in self.dates:
            date = datetime.strptime(str_, "%Y-%m-%d %H:%M:%S")
            tzdate = naive_tzinfo.UTCTimeZone(date)
            self.assertEqual(int(tzdate.utcoffset(date).seconds / 3600), 0)

    def test_calcs(self):
        """Border dates for couple of years"""

        for str_ in self.dates:
            date = datetime.strptime(str_, "%Y-%m-%d %H:%M:%S")
            tzdate = naive_tzinfo.UTCTimeZone(date)
            self.assertEqual(tzdate.tzname(date), "UTC")


class TestCETimeZone(unittest.TestCase):
    """CET/CEST tzinfo class tests"""

    def setUp(self):
        """Setup"""
        self.dates = {'2012-03-25 02:00:00': "CEST",
                      '2013-03-31 02:00:00': "CEST",
                      '2014-03-30 02:00:00': "CEST",
                      '2015-03-29 02:00:00': "CEST",
                      '2016-03-27 02:00:00': "CEST",
                      '2005-03-27 02:00:00': "CEST",
                      '2006-03-26 02:00:00': "CEST",
                      '2007-03-25 02:00:00': "CEST",
                      '2008-03-30 02:00:00': "CEST",
                      '2009-03-29 02:00:00': "CEST",
                      '2010-03-28 02:00:00': "CEST",
                      '2011-03-27 02:00:00': "CEST",
                      '2012-03-25 01:59:59': "CET",
                      '2013-03-31 01:59:59': "CET",
                      '2014-03-30 01:59:59': "CET",
                      '2015-03-29 01:59:59': "CET",
                      '2016-03-27 01:59:59': "CET",
                      '2005-03-27 01:59:59': "CET",
                      '2006-03-26 01:59:59': "CET",
                      '2007-03-25 01:59:59': "CET",
                      '2008-03-30 01:59:59': "CET",
                      '2009-03-29 01:59:59': "CET",
                      '2010-03-28 01:59:59': "CET",
                      '2011-03-27 01:59:59': "CET",
                      '2012-10-28 01:59:59': "CEST",
                      '2013-10-27 01:59:59': "CEST",
                      '2014-10-26 01:59:59': "CEST",
                      '2015-10-25 01:59:59': "CEST",
                      '2016-10-30 01:59:59': "CEST",
                      '2005-10-30 01:59:59': "CEST",
                      '2006-10-29 01:59:59': "CEST",
                      '2007-10-28 01:59:59': "CEST",
                      '2008-10-26 01:59:59': "CEST",
                      '2009-10-25 01:59:59': "CEST",
                      '2010-10-31 01:59:59': "CEST",
                      '2011-10-30 01:59:59': "CEST",
                      '2012-10-28 02:00:00': "CET",
                      '2013-10-27 02:00:00': "CET",
                      '2014-10-26 02:00:00': "CET",
                      '2015-10-25 02:00:00': "CET",
                      '2016-10-30 02:00:00': "CET",
                      '2005-10-30 02:00:00': "CET",
                      '2006-10-29 02:00:00': "CET",
                      '2007-10-28 02:00:00': "CET",
                      '2008-10-26 02:00:00': "CET",
                      '2009-10-25 02:00:00': "CET",
                      '2010-10-31 02:00:00': "CET",
                      '2011-10-30 02:00:00': "CET"}

    def test_utcoffset(self):
        """Tests of utf offsets"""
        map_ = {'CEST': 2, 'CET': 1}

        for str_, tzone in self.dates.items():
            date = datetime.strptime(str_, "%Y-%m-%d %H:%M:%S")
            tzdate = naive_tzinfo.CETimeZone(date)
            self.assertEqual(int(tzdate.utcoffset(date).seconds / 3600),
                             map_[tzone])

    def test_calcs(self):
        """Border dates for couple of years"""

        for str_, tzone in self.dates.items():
            date = datetime.strptime(str_, "%Y-%m-%d %H:%M:%S")
            tzdate = naive_tzinfo.CETimeZone(date)
            self.assertEqual(tzdate.tzname(date), tzone,
                             "date `%s' should have timezone `%s', but it "
                             "have `%s'" % (str_, tzone, tzdate.tzname(date)))


class TestFunctions(unittest.TestCase):
    """Test "interface" functions"""

    def setUp(self):
        """Setup"""
        self._pytz = naive_tzinfo.pytz
        naive_tzinfo.pytz = None

    def tearDown(self):
        """Setup"""
        naive_tzinfo.pytz = self._pytz

    def test_get_rfc3339(self):
        """test get_rfc3339 method for CET/CEST"""
        date_ = datetime.strptime("2010-01-25 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc3339(date_, "Europe/Warsaw"),
                         "2010-01-25T20:20:00+0100")
        date_ = datetime.strptime("2010-06-29 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc3339(date_, "Europe/Warsaw"),
                         "2010-06-29T20:20:00+0200")

        date_ = datetime.strptime("2010-01-25 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc3339(date_, "UTC"),
                         "2010-01-25T20:20:00+0000")
        date_ = datetime.strptime("2010-06-29 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc3339(date_, "UTC"),
                         "2010-06-29T20:20:00+0000")

        date_ = datetime.strptime("2010-06-29 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertRaises(KeyError, naive_tzinfo.get_rfc3339, date_,
                          "Europe/Berlin")

    def test_get_rfc822(self):
        """test get_rfc822 method for CET/CEST"""
        date_ = datetime.strptime("2010-01-28 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc822(date_, "Europe/Warsaw"),
                         "Thu, 28 Jan 2010 20:20:00 +0100")

        date_ = datetime.strptime("2010-06-29 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc822(date_, "Europe/Warsaw"),
                         "Tue, 29 Jun 2010 20:20:00 +0200")

        date_ = datetime.strptime("2010-01-28 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc822(date_, "UTC"),
                         "Thu, 28 Jan 2010 20:20:00 +0000")

        date_ = datetime.strptime("2010-06-29 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertRaises(KeyError, naive_tzinfo.get_rfc822, date_,
                          "Europe/Berlin")


class TestPytzFunction(unittest.TestCase):
    """Test functionality, if pytz module exists."""

    def setUp(self):
        """Setup"""
        self._pytz = None
        if not naive_tzinfo.pytz:
            # mock pytz if not avail
            self._pytz = naive_tzinfo.pytz
            naive_tzinfo.pytz = CommonMock()
            naive_tzinfo.pytz.timezone = lambda x: MockPytzTimezone()

    def tearDown(self):
        """Setup"""
        if self._pytz:
            naive_tzinfo.pytz = self._pytz

    def test_get_rfc3339(self):
        """test get_rfc3339 method for CET/CEST"""
        date_ = datetime.strptime("2010-06-29 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc3339(date_, "Europe/Berlin"),
                         "2010-06-29T20:20:00+0200")

    def test_get_rfc822(self):
        """test get_rfc822 method for CET/CEST"""
        date_ = datetime.strptime("2010-06-29 20:20:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(naive_tzinfo.get_rfc822(date_, "Europe/Berlin"),
                         "Tue, 29 Jun 2010 20:20:00 +0200")


if __name__ == '__main__':
    unittest.main()
