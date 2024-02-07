__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

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
