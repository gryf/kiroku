#!/usr/bin/env python3
# encoding: utf-8
"""
Tests for tzinfo naive implementation

"""

from datetime import datetime
import unittest

import naive_tzinfo


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

if __name__ == '__main__':
    unittest.main()
