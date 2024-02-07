__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

import abc

from .base import BaseModel


class PaymentType(BaseModel):
    @property
    @abc.abstractmethod
    def method(self):
        """Hold the type as str."""
        pass

    def __init__(
            self,
            key=None,
            **kwargs
    ):
        """Create a new paymentType ressource.

        :param key: (optional) (original: id) ID for this payment type
        :type key: str
        """
        self.key = key  # type: str

    def serialize(self):
        return {}

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)

    @classmethod
    def construct(cls, method):
        sub_cls = type(str(method).title(), (cls,), {"method": method})
        return sub_cls
