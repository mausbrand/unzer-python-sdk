import abc
import logging
import typing as t

from ..base import BaseModel

if t.TYPE_CHECKING:
    from ..payment import PaymentTypes, PaymentMethodTypes  # noqa

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class PaymentType(BaseModel):
    @property
    @abc.abstractmethod
    def method(self) -> "PaymentTypes":
        """Hold the type."""
        pass

    @property
    @abc.abstractmethod
    def method_name(self) -> "PaymentMethodTypes":
        """Hold the full payment name."""
        pass

    # TODO: Rename method and method_name (Unzer himself has no clear concept or consistent naming for this either)

    def __init__(
            self,
            key: str = None,
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
    def get_subclasses(cls) -> t.Type[t.Self]:
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def construct(cls, method: "PaymentTypes") -> t.Type["PaymentType"]:
        for subclass in PaymentType.get_subclasses():
            if subclass.method == method:
                return subclass
        logger.warning(f"Creating not existing PaymentType for method {method} on the fly")
        sub_cls = type(str(method).title(), (cls,), {"method": method, "method_name": "N/A"})
        return sub_cls  # noqa

    def get_configuration(self) -> dict:
        if self._client is None:
            raise IOError(f"PaymentType {type(self).__name__} was not initialized with client instance")
        key_pair_types = self._client.getKeyPairTypes()
        logger.debug(f"key_pair_types: {key_pair_types}")
        for payment_type in key_pair_types["paymentTypes"]:
            if payment_type["type"] == self.method_name.value:
                return payment_type
        raise LookupError(f"PaymentType {self.method_name} is not configured in the keypair")

    # TODO: Without caching this isn't the best solution --> better implement in the KeyPairTypeModel
    def get_channel_id(self) -> str:
        return self.get_configuration()["supports"][0]["channel"]

    def get_brands(self) -> list[str]:
        return self.get_configuration()["supports"][0]["brands"]
