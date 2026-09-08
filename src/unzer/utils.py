import datetime
import re


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


def normalize_language(value: str | None) -> str | None:
    """Normalize a language code the way the customer resource expects it.

    :param value: An ISO 639-1 code, in any case (e.g. ``de`` or ``DE``).
    :return: The lowercase code, or ``None`` for an empty value.
    :raises ValueError: For anything that is not a two letter code.

    The API takes the bare lowercase code only; everything else fails with
    HTTP 400 ``API.410.200.057`` *language is invalid.* (measured against the
    sandbox), so a wrongly cased code is normalized here instead of rejected.
    """
    if not value:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Invalid value {value!r}")
    if not re.fullmatch(r"[A-Za-z]{2}", value):
        # Anything that is not a two letter code (e.g. the locale 'de-DE') would fail
        # in the request; raise here to fail before it is sent.
        raise ValueError(f"Invalid language {value!r}, expected an ISO 639-1 code like 'de'")
    return value.lower()
