import abc
import enum
import logging
import typing as t

from ..base import BaseModel

if t.TYPE_CHECKING:
    from ..payment import PaymentTypes, PaymentMethodTypes  # noqa

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class _UnknownMethodName:
    """Stand-in for the URL slug of a payment type the SDK does not know.

    Accessing :attr:`value` raises instead of handing a useless string to the
    request builder, so the error names the actual problem.
    """

    @property
    def value(self) -> str:
        """Always raises: an unimplemented payment type has no resource path."""
        raise NotImplementedError(
            "This payment type has no implementation in this SDK, so its resource "
            "path is unknown. It can be used to read existing payments, but not to "
            "create a new payment type."
        )

    def __repr__(self) -> str:
        return "<unknown method name>"


class PaymentType(BaseModel):
    """Base class of every payment method.

    A payment type is a resource at Unzer, and its id (``s-crd-...``) is what a
    payment refers to. Two names identify the method, and they differ:
    :attr:`method` is the three-letter short code inside that id, while
    :attr:`method_name` is the slug in the ``types/`` path.

    Which of the two ways a type comes into being decides whether its subclass
    carries fields at all -- server-side for seven of them, in the browser for the
    rest, whose classes are deliberately empty.

    .. seealso:: ../../../docs/payment-methods.md
    """

    @property
    @abc.abstractmethod
    def method(self) -> "PaymentTypes":
        """Hold the type."""

    @property
    @abc.abstractmethod
    def method_name(self) -> "PaymentMethodTypes":
        """Hold the full payment name."""

    # TODO: Rename method and method_name (Unzer himself has no clear concept or consistent naming for this either)

    def __init__(
            self,
            key: str | None = None,
            **kwargs
    ):
        """Create a new paymentType ressource.

        :param key: (optional) (original: id) ID for this payment type
        """
        super().__init__(**kwargs)
        self.key: str = key

    def serialize(self) -> dict:
        return {}

    @classmethod
    def fromDict(cls, data: dict) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)

    @classmethod
    def get_subclasses(cls) -> t.Iterator[type[t.Self]]:
        """Yield every payment type class, including those of subclasses."""
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def construct(cls, method: "PaymentTypes") -> type["PaymentType"]:
        """Find the class implementing a payment method.

        For a method this SDK does not implement -- a discontinued or deprecated
        one -- a placeholder class is built, so that existing payments still read
        back. That placeholder cannot create a new payment type: asking it for its
        resource path raises.

        :param method: The short code of the method, as it appears in a type id.
        :return: The class, not an instance.
        """
        for subclass in PaymentType.get_subclasses():
            if subclass.method == method:
                return subclass
        logger.warning(f"Creating not existing PaymentType for method {method} on the fly")
        short = (method.name.title().replace("_", "")
                 if isinstance(method, enum.Enum) else str(method).title())
        name = f"{short}PaymentType"
        # method_name must stay an enum member: the client reads `.value` off it to
        # build the resource path. There is no slug for an unknown type, so the
        # placeholder raises on use instead of failing with an AttributeError.
        sub_cls = type(name, (cls,), {"method": method, "method_name": _UnknownMethodName()})
        return sub_cls  # noqa

    def get_configuration(self) -> dict:
        """Provide the keypair configuration for this payment type.

        Returns the first entry when the keypair holds several, which it can --
        see :meth:`get_configurations`. Prefer passing a brand to
        :meth:`get_channel_id` over relying on the order here.

        :raises LookupError: If the payment type is not configured at all.
        :raises RuntimeError: If this payment type was created without a client.
        """
        configurations = self.get_configurations()
        if len(configurations) > 1:
            logger.warning(
                f"Keypair holds {len(configurations)} configurations for "
                f"{self.method_name}, using the first one"
            )
        return configurations[0]

    def get_configurations(self) -> list[dict]:
        """Provide every keypair configuration for this payment type.

        A keypair can hold more than one entry per payment type -- observed with
        ``card``, where two entries differ in their supported brands and channel.
        :meth:`get_configuration` returns only the first one, so use this method
        when the distinction matters.

        :raises LookupError: If the payment type is not configured at all.
        """
        if self._client is None:
            raise RuntimeError(
                f"{type(self).__name__} was created without a client, so it cannot "
                f"read its keypair configuration. Pass client= to the constructor, "
                f"or use the instance the client returned."
            )
        key_pair_types = self._client.getKeyPairTypes()
        logger.debug(f"key_pair_types: {key_pair_types!r}")
        # Compared case-insensitive: Unzer is not consistent about the casing of the
        # method names -- the API really does answer with *EPS* while the resource
        # path is *eps*.
        wanted = self.method_name.value.lower()
        configurations = [
            payment_type
            for payment_type in key_pair_types["paymentTypes"]
            if payment_type["type"].lower() == wanted
        ]
        if not configurations:
            raise LookupError(f"PaymentType {self.method_name} is not configured in the keypair")
        return configurations

    # TODO: Without caching this isn't the best solution --> better implement in the KeyPairTypeModel
    def get_channel_id(self, brand: str | None = None) -> str:
        """Provide the channel id configured for this payment type.

        :param brand: (optional) Restrict the lookup to the configuration that
            supports this brand (e.g. ``AMEX``). Required whenever a keypair holds
            several configurations for one payment type -- a real keypair was seen
            with two ``card`` entries, one for ``MASTER``/``VISA`` and one for
            ``AMEX``, each on its own channel. Without the brand the first entry
            wins, which is the wrong channel for every other brand.
        :raises LookupError: If no configuration supports the requested brand.
        """
        return self._support(brand)["channel"]

    def get_brands(self, brand: str | None = None) -> list[str]:
        """Provide the card brands this payment type accepts.

        :param brand: (optional) See :meth:`get_channel_id`.
        """
        return self._support(brand)["brands"]

    def _support(self, brand: str | None = None) -> dict:
        """Pick the ``supports`` entry to read channel and brands from."""
        configurations = self.get_configurations()
        supports = [
            support
            for configuration in configurations
            for support in configuration.get("supports") or []
        ]
        if brand is not None:
            matching = [s for s in supports if brand.upper() in
                        {str(b).upper() for b in s.get("brands") or []}]
            if not matching:
                available = sorted({b for s in supports for b in s.get("brands") or []})
                raise LookupError(
                    f"No configuration of {self.method_name} supports the brand "
                    f"{brand!r}. Available: {available}"
                )
            supports = matching
        if not supports:
            raise LookupError(f"PaymentType {self.method_name} has no supports entry")
        if len(supports) > 1:
            logger.warning(
                f"{self.method_name} has {len(supports)} configurations; using the "
                f"first one. Pass brand= to choose."
            )
        return supports[0]
