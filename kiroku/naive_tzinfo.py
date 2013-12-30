"""
Naive implementation of tzinfo class for CET/CEST timezone for Kiroku.
Prefer to use pytz[1] if available.

[1] http://pytz.sourceforge.net/
"""
from datetime import tzinfo, timedelta, datetime

try:
    import pytz
except ImportError:
    pytz = None


ZERO = timedelta(0)
HOUR = timedelta(hours=1)


def first_sunday_on_or_after(dt_arg):
    """return date with the first sunday from the provided date"""
    days_to_go = 6 - dt_arg.weekday()
    if days_to_go:
        dt_arg += timedelta(days_to_go)
    return dt_arg


class UTCTimeZone(tzinfo):
    """UTC time zone naive implementation"""
    def tzname(self, dt_arg):
        """tzinfo.tzname implementation"""
        return "UTC"

    def dst(self, dt_arg):
        """tzinfo.dst implementation"""
        return None

    def utcoffset(self, dt_arg):
        """tzinfo.utcoffset implementation"""
        return timedelta(hours=0)

    def localize(self, dt_arg):
        """return datetime from the argument updated with the timezone info"""
        return dt_arg.replace(tzinfo=self)


class CETimeZone(tzinfo):
    """CET/CEST time zone naive implementation"""

    def tzname(self, dt_arg):
        """tzinfo.tzname implementation"""
        if self.dst(dt_arg):
            return "CEST"
        else:
            return "CET"

    def dst(self, dt_arg):
        """tzinfo.dst implementation"""

        dststart = datetime(1, 3, 25, 2)
        dstend = datetime(1, 10, 25, 2)

        start = first_sunday_on_or_after(dststart.replace(year=dt_arg.year))
        end = first_sunday_on_or_after(dstend.replace(year=dt_arg.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt_arg first.
        if start <= dt_arg.replace(tzinfo=None) < end:
            return timedelta(hours=1)
        else:
            return None

    def utcoffset(self, dt_arg):
        """tzinfo.utcoffset implementation"""
        delta = timedelta(hours=1)
        dst_delta = self.dst(dt_arg)
        if dst_delta:
            delta += dst_delta
        return delta

    def localize(self, dt_arg):
        """return datetime from the argument updated with the timezone info"""
        return dt_arg.replace(tzinfo=self)


TIMEZONE_MAP = {'UTC': UTCTimeZone,
                'Europe/Warsaw': CETimeZone}


def _get_formatted_date(datetime_arg, zone_string, format_):
    """Return datetime as provided formatted string"""
    if pytz:
        tzone = pytz.timezone(zone_string)
    else:
        # Fallback to naive implementation
        tzone = TIMEZONE_MAP[zone_string](datetime_arg)

    tz_dt = tzone.localize(datetime_arg)

    return tz_dt.strftime(format_)


def get_rfc3339(datetime_arg, zone_string):
    """Return RFC 3339 formatted string out of datetime provided object"""
    return _get_formatted_date(datetime_arg, zone_string,
                               '%Y-%m-%dT%H:%M:%S%z')


def get_rfc822(datetime_arg, zone_string):
    """Return RFC 822 formatted string out of datetime provided object"""
    return _get_formatted_date(datetime_arg, zone_string,
                               '%a, %d %b %Y %X %z')
