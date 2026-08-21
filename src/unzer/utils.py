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
    if "." in value:  # European Date
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


def roundAmount(value: float | int | str | None) -> float | None:
    """Round a monetary amount to the four decimal places the API accepts.

    The API specifies amounts as ``Decimal{10,4}``. Two things go wrong without
    this. Floating point arithmetic produces residues -- ``12.3 - 10.0 - 2.3`` is
    ``8.88e-16``, not ``0`` -- and :func:`json.dumps` writes those in scientific
    notation, which is not a number the API accepts. And an amount carrying more
    than four decimals is silently truncated on their side.

    :param value: The amount, or ``None``.
    :return: The rounded amount, or ``None`` if there was none.
    """
    if value is None or value == "":
        return None
    return round(float(value), 4)


def parseTimestamp(value: str | int | float | None) -> datetime.datetime | None:
    """Parse a unix timestamp that may be in seconds or in milliseconds.

    The API reference gives ``expiresAt`` as ``1735689599`` -- ten digits, seconds.
    The API actually answers with thirteen digits, milliseconds. Reading that as
    seconds lands in the year 58608 and raises, which made
    :meth:`UnzerClient.getPaylaterInstallmentPlans` unusable.

    Rather than picking one unit, the magnitude decides: anything past the year
    5138 in seconds is milliseconds.

    :param value: The timestamp, as string or number.
    :return: The parsed datetime, or ``None`` if there was no value.
    """
    if value is None or value == "":
        return None
    timestamp = float(value)
    if abs(timestamp) > 1e11:
        timestamp /= 1000
    return datetime.datetime.fromtimestamp(timestamp)
