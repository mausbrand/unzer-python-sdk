"""Conversions between the wire format and Python types.

The API is inconsistent about how it encodes values -- amounts arrive as
strings, dates in two different formats, timestamps in a unit its own reference
gets wrong -- so these helpers exist to keep that out of the models.
"""
import datetime
import re


class Sentinel:
    """A value for *not given*, for cases where ``None`` is a value of its own.

    An argument that defaults to ``None`` cannot tell "the caller said nothing"
    from "the caller said explicitly: no value". Where that difference matters,
    default to :data:`SENTINEL` instead and compare with ``is`` -- identity is
    what carries the meaning.

    Its ``repr`` is ``<SENTINEL>``, and it is falsy, so ``if not value`` treats
    it like an empty value. Both match the ``Sentinel`` of viur-shop: the two
    cannot share one definition (neither package may depend on the other), so
    they at least behave the same.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        # A bare object() would show as "<object object at 0x...>" in tracebacks
        # and reprs, which says nothing about what went wrong.
        return "<SENTINEL>"

    def __bool__(self) -> bool:
        return False


SENTINEL = Sentinel()
"""The one instance of :class:`Sentinel`, used as *not given* default."""


def parseBool(value: object) -> bool:
    """Read a boolean the API sent as the string ``"true"`` or ``"false"``."""
    return str(value).lower() == "true"


def parseDateTime(value: str | datetime.datetime | None) -> datetime.datetime | None:
    """Parse a timestamp in either of the two formats the API uses.

    ``2026-08-21 10:15:32`` and ``21.08.2026 10:15:32`` are both accepted.

    :raises TypeError: If the string matches neither format.
    """
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if "-" in value:  # ISO Date
        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    if "." in value:  # European Date
        return datetime.datetime.strptime(value, "%d.%m.%Y %H:%M:%S")
    raise TypeError(f"Invalid date format of {value!r}")


def parseDate(value):
    """Parse a date without a time part (e.g. ``2023-08-20``)."""
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def parse_birth_date(
        value: str | datetime.date | datetime.datetime | None,
) -> datetime.datetime | datetime.date | None:
    """Parse a date of birth in either of the two formats the API documents.

    ``1990-01-24`` and ``24.01.1990`` are both read; a :class:`~datetime.date` or
    :class:`~datetime.datetime` is taken as is. In the sandbox both formats were
    accepted for the ``birthdate`` of a company owner, and read back in ISO form.

    :param value: The date of birth, or an empty value.
    :return: The parsed date, or ``None`` if there was none.
    :raises TypeError: For a string in neither format, or an unusable type.
    """
    if not value:
        return None
    if isinstance(value, str):
        if "-" in value:  # ISO Date
            return datetime.datetime.strptime(value, "%Y-%m-%d")
        if "." in value:  # European Date
            return datetime.datetime.strptime(value, "%d.%m.%Y")
        raise TypeError(f"Invalid date format of {value!r}")
    if not isinstance(value, (datetime.datetime, datetime.date)):
        raise TypeError(f"Invalid value {value!r}")
    return value


def format_birth_date(value: datetime.date | str | None) -> str | None:
    """Write a date of birth in ISO form, ``YYYY-MM-DD``.

    :param value: A parsed date, or a string that is passed on unchanged.
    :return: ``YYYY-MM-DD``, the string as given, or ``None``.
    """
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.strftime("%Y-%m-%d")
    return value


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
        # Anything that is not a two letter code (e.g. the locale "de-DE") would fail
        # in the request; raise here to fail before it is sent.
        raise ValueError(f"Invalid language {value!r}, expected a two letter ISO 639-1 code")
    return value.lower()
