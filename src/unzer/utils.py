import datetime


def parseBool(value):
    return str(value).lower() == "true"


def parseDateTime(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if "-" in value:  # ISO Date
        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    elif "." in value:  # European Date
        return datetime.datetime.strptime(value, "%d.%m.%Y %H:%M:%S")
    raise TypeError("Invalid date format of %r" % value)


def parseDate(value):
    """Parse a date without a time part (e.g. ``2023-08-20``)."""
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def parseFloat(value):
    """Parse an optional amount, which the API sends as string."""
    if value is None or value == "":
        return None
    return float(value)
