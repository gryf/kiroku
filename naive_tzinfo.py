"""
Naive implementation of tzinfo class for CET/CEST timezone for Kiroku.
"""
from datetime import tzinfo, timedelta, datetime

ZERO = timedelta(0)
HOUR = timedelta(hours=1)


def first_sunday_on_or_after(dt_arg):
    """return date with the first sunday from the provided date"""
    days_to_go = 6 - dt_arg.weekday()
    if days_to_go:
        dt_arg += timedelta(days_to_go)
    return dt_arg


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


def _get_formatted_date(datetime_arg, format_):
    """Return datetime as provided formatted string"""
    tzone = CETimeZone(datetime_arg)
    tz_dt = datetime_arg.replace(tzinfo=tzone)
    return tz_dt.strftime(format_)


def get_rfc3339(datetime_arg):
    """Return RFC 3339 formatted string out of datetime provided object"""
    return _get_formatted_date(datetime_arg, '%Y-%m-%dT%H:%M:%S%z')


def get_rfc822(datetime_arg):
    """Return RFC 822 formatted string out of datetime provided object"""
    return _get_formatted_date(datetime_arg, '%a, %d %b %Y %X %z')
