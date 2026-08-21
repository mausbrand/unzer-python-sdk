import datetime
import logging

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class Error:
    def __init__(self, code, merchantMessage, customerMessage, **kwargs):
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
    def fromDict(cls, data, message="Unzer Error"):
        return cls(
            message,
            timestamp=datetime.datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S"),
            url=data["url"],
            errors=[Error(**error) for error in data["errors"]],
            errorId=data.get("id"),
            traceId=data.get("traceId"),
            isError=data.get("isError"),
            isPending=data.get("isPending"),
            isSuccess=data.get("isSuccess"),
        )

    def __repr__(self):
        return (
            f"{self.__class__.__module__}.{self.__class__.__name__}("
            f"url={self.url!r}, errorId={self.errorId!r}, "
            f"traceId={self.traceId!r}, errors={self.errors!r})"
        )
