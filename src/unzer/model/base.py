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

    MAX_LENGTHS: t.ClassVar[dict[str, int]] = {}
    """Longest value the API accepts per attribute, checked by :meth:`validateBeforeRequest`.

    The numbers are measured against the sandbox, not read off the documentation --
    see ``examples/06_probe_field_limits.py``. Several of the documented limits are
    wrong, so an entry here without a measurement behind it is worse than none.

    Keys are attribute names and may be properties: an address is limited on its
    joined :attr:`~unzer.model.address.Address.name`, not on the two parts it is
    built from.
    """

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

    def bind_client(self, client: "UnzerClient") -> t.Self:
        """Attach a client to this model, unless it already has one.

        A model with a client can reach the API on its own (as
        :meth:`~unzer.model.payment.PaymentResponse.charge` does) and can fall
        back to the settings of that client (as the language of a
        :class:`~unzer.model.customer.Customer` does). The client methods that
        send or receive a model bind themselves to it, so the caller does not
        have to pass the client twice.

        An already attached client is kept: an object that was built for one
        client must not silently start talking to another one.

        This is a method and not a property on purpose -- :meth:`asDict`,
        :meth:`__iter__` and :meth:`__repr__` skip the underscore attributes
        but do include properties, and the client has no place in the data of
        a model.

        :param client: The client to attach.
        :return: The model itself, to allow ``model.bind_client(self).serialize()``.
        """
        if self._client is None:
            self._client = client
        return self

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
        By default, check for the required attributes, set in
        :attr:`REQUIRED_ATTRIBUTES`, and the field lengths, set in
        :attr:`MAX_LENGTHS` (both class attributes).

        :raises ValueError: If an attribute is missing or too long for the API.
        """
        for attr in type(self).REQUIRED_ATTRIBUTES:  # use always the cls-attributes
            if not getattr(self, attr):
                raise ValueError(f"{type(self).__name__} misses the attribute *{attr}*.")
        for attr, limit in type(self).MAX_LENGTHS.items():
            value = getattr(self, attr)
            if value is not None and len(str(value)) > limit:
                raise ValueError(
                    f"{type(self).__name__}.{attr} is {len(str(value))} characters long, "
                    f"but the API accepts at most {limit}."
                )
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
