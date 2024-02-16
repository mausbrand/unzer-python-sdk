import abc
import logging
import typing as t

from ..base import BaseModel

if t.TYPE_CHECKING:
    from .. import PaymentTypes

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class PaymentType(BaseModel):
    @property
    @abc.abstractmethod
    def method(self) -> "PaymentTypes":
        """Hold the type."""
        pass

    def __init__(
            self,
            key: str = None,
            **kwargs
    ):
        """Create a new paymentType ressource.

        :param key: (optional) (original: id) ID for this payment type
        """
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
        sub_cls = type(str(method).title(), (cls,), {"method": method})
        return sub_cls  # noqa
