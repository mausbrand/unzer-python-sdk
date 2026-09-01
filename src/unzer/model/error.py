import datetime
import logging
import typing as t

from ..utils import parseDateTime

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class Error:
    """A single error entry of an API response.

    The API answers with a list of these. :attr:`merchantMessage` is the one worth
    logging; :attr:`customerMessage` is meant to be shown to the customer and is
    translated according to the language the client was built with.

    .. seealso:: https://docs.unzer.com/server-side-integration/api-basics/error-handling/
    """

    def __init__(
            self,
            code: str | None = None,
            merchantMessage: str | None = None,
            customerMessage: str | None = None,
            **kwargs: t.Any,
    ) -> None:
        self.code = code
        self.merchantMessage = merchantMessage
        self.customerMessage = customerMessage
        if kwargs:
            logger.warning("Error got additional unhandled data: %r", kwargs)

    def __str__(self):
        return f"{self.__class__.__name__} {self.code}: {self.merchantMessage}"

    def __repr__(self):
        return (
            f"{self.__class__.__module__}.{self.__class__.__name__}("
            f"code={self.code!r}, merchantMessage={self.merchantMessage!r}, "
            f"customerMessage={self.customerMessage!r})"
        )


class ErrorResponse(Exception):
    """Raised when the API reports an error.

    Carries the whole payload: the individual :attr:`errors`, the
    :attr:`errorId` (``s-err-...``, which Unzer support can resolve), the
    :attr:`traceId` and the HTTP :attr:`statusCode`. :attr:`srcResponse` holds the
    raw :class:`requests.Response`.

    Note that the API can report an error **with a 2xx status code** -- a payload
    carrying ``isError`` raises just the same.
    """

    def __init__(
            self,
            message,
            timestamp=None,
            url=None,
            errors=None,
            errorId=None,
            statusCode=0,
            traceId=None,
            isError=None,
            isPending=None,
            isSuccess=None,
            srcResponse=None,
            **kwargs

    ):
        super().__init__(message)
        if errors is None:
            errors = []
        self.timestamp = timestamp  # type: str
        self.url = url  # type: str
        self.errors = errors  # type: list[Error]
        self.errorId = errorId  # type: str
        self.statusCode = statusCode  # type: int
        self.traceId = traceId  # type: str
        self.isError = isError  # type: bool
        self.isPending = isPending  # type: bool
        self.isSuccess = isSuccess  # type: bool
        self.srcResponse = srcResponse  # type: requests.Response
        if kwargs:
            logger.warning("ErrorResponse got additional unhandled data: %r", kwargs)

    @classmethod
    def fromDict(cls, data: t.Any, message: str = "Unzer Error") -> "ErrorResponse":
        """Build an ErrorResponse from a decoded API error body.

        Only ``errors`` is treated as required, because it is what identifies the
        body as this API's error envelope and it is the one part a caller acts on --
        `UnzerClient.createOrUpdateCustomer` branches on ``errors[0].code``. Anything
        else missing or unreadable costs that field alone, never the list: an error
        that cannot be reported is worse than one reported without its timestamp.

        :param data: The decoded body.
        :param message: The exception message.
        :raises ValueError: If ``data`` is not an error envelope, so the caller can
            tell "the API refused this" from "something else answered".
        :return: The error response.
        """
        if not isinstance(data, dict) or "errors" not in data:
            raise ValueError(f"Not an API error envelope: {data!r}")
        return cls(
            message,
            timestamp=cls._parseTimestamp(data.get("timestamp")),
            url=data.get("url"),
            errors=[Error(**error) for error in data.get("errors") or []],
            errorId=data.get("id"),
            traceId=data.get("traceId"),
            isError=data.get("isError"),
            isPending=data.get("isPending"),
            isSuccess=data.get("isSuccess"),
        )

    @staticmethod
    def _parseTimestamp(value: str | datetime.datetime | None) -> datetime.datetime | None:
        """Read the error timestamp, tolerating a format the SDK does not know.

        The API is known to use two formats and has been seen with others; losing the
        error codes over the one field nobody branches on is not a trade worth making.

        :param value: The raw ``timestamp`` value.
        :return: The parsed timestamp, or ``None`` if it cannot be read.
        """
        try:
            return parseDateTime(value)
        except (TypeError, ValueError):
            logger.warning(f"Cannot parse the error timestamp {value!r}")
            return None

    def __repr__(self):
        return (
            f"{self.__class__.__module__}.{self.__class__.__name__}("
            f"url={self.url!r}, errorId={self.errorId!r}, "
            f"traceId={self.traceId!r}, errors={self.errors!r})"
        )
