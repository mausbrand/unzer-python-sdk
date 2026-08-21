import datetime
import typing as t

from ..utils import parseBool, parseDateTime
from .base import BaseModel, JSONValue


class RiskCheckResponse(BaseModel):
    """Response of a customer risk check.

    .. seealso:: :meth:`unzer.UnzerClient.riskCheckPaylaterInstallment`
    """

    def __init__(
            self,
            key: str = None,
            url: str = None,
            timestamp: datetime.datetime = None,
            isSuccess: bool = None,
            isPending: bool = None,
            isResumed: bool = None,
            isError: bool = None,
            **kwargs,
    ):
        """Create a new RiskCheckResponse.

        :param key: (original: id) Id of this risk check (e.g. ``GHZC-PQVK-RLGP``).
        :param url: (optional) URL of the checked resource.
        :param timestamp: (optional) Time of the check.
        :param isSuccess: (optional) The risk check was accepted.
        :param isPending: (optional)
        :param isResumed: (optional) (original: isResume) The API reference and the
            accepted response spell this ``isResume``, the declined one ``isResumed``.
        :param isError: (optional) The risk check was declined.
        """
        super().__init__(**kwargs)
        self.key = key
        self.url = url
        self.timestamp = timestamp
        self.isSuccess = isSuccess
        self.isPending = isPending
        self.isResumed = isResumed
        self.isError = isError

    def serialize(self) -> dict[str, JSONValue]:
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        data["timestamp"] = parseDateTime(data.get("timestamp"))
        for key in ("isSuccess", "isPending", "isError"):
            data[key] = parseBool(data[key]) if key in data else None
        # Unzer uses both spellings: isResume in the API reference and in the accepted
        # response, isResumed in the declined response
        if "isResumed" in data or "isResume" in data:
            data["isResumed"] = parseBool(data.get("isResumed", data.get("isResume")))
        else:
            data["isResumed"] = None
        return cls(**data)
