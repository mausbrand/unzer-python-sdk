"""The base class every resource model derives from."""
import abc
import typing as t

if t.TYPE_CHECKING:
    from ..client import UnzerClient  # pylint: disable=unused-import

JSONValue: t.TypeAlias = str | int | float | bool | list["JSONValue"] | dict[str, "JSONValue"] | None


class BaseModel(abc.ABC):
    """Base class for every resource model.

    A model is a plain Python object mirroring one API resource. It converts in
    both directions: :meth:`serialize` builds the request payload,
    :meth:`fromDict` reads a response. Response-only models raise
    :exc:`NotImplementedError` from :meth:`serialize`, and request-only models do
    the same from :meth:`fromDict`.

    Subclasses list the attributes the API insists on in
    :attr:`REQUIRED_ATTRIBUTES`, which :meth:`validateBeforeRequest` checks before
    a request goes out -- catching a missing field here saves a round trip and
    gives a clearer error than the API's.
    """

    EMPTY_STRING = ""

    REQUIRED_ATTRIBUTES: t.ClassVar[list[str]] = []

    def __init__(
            self,
            client: "UnzerClient" = None,
            **kwargs,
    ):
        """
        :param client: (optional) The client instance.
        """
        super().__init__()
        self._client: UnzerClient = client

    def getString(self, value: object) -> object:
        """Turn ``None`` into an empty string for fields the API wants as text.

        Only for string fields: an object field rejects an empty string. Sending
        ``billingAddress: ""`` for a missing address made the API answer
        ``400 API.410.300.007``.
        """
        if value is None:
            return self.EMPTY_STRING
        return value

    @abc.abstractmethod
    def serialize(self) -> dict[str, JSONValue]:
        """Serialize data from an object as dict for the request-payload."""

    @classmethod
    @abc.abstractmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        """Unserialize data from a dict from a response to new object"""

    def validateBeforeRequest(self) -> bool:
        """Validate the model.

        Useful to check the model for validity before the API request.
        By default, check for the required attributes,
        set in :attr:`REQUIRED_ATTRIBUTES` (class attribute).
        """
        for attr in type(self).REQUIRED_ATTRIBUTES:  # use always the cls-attributes
            if not getattr(self, attr):
                raise ValueError(f"{type(self).__name__} misses the attribute *{attr}*.")
        return True

    def __repr__(self) -> str:
        return "{}.{}({})".format(
            self.__class__.__module__,
            self.__class__.__name__,
            ", ".join(f"{k}={v!r}" for k, v in sorted(self))
        )

    def asDict(self) -> dict[str, t.Any]:
        """Return the model as dict.

        This will not be done recursive.
        """
        # instance attributes
        data = {k: v for k, v in vars(self).items() if not k.startswith("_")}
        # class properties
        for k, v in vars(self.__class__).items():
            if isinstance(v, property):
                data[k] = getattr(self, k)
        return data

    def __iter__(self):
        """Yield the attributes of the model"""
        yield from self.asDict().items()
