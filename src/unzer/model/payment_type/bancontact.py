import typing as t

from unzer.model.payment import PaymentTypes
from .abstract_paymenttype import PaymentType


class Bancontact(PaymentType):
    method = PaymentTypes.BANCONTACT

    REQUIRED_ATTRIBUTES = ["holder"]

    def __init__(
            self,
            holder: str,
            **kwargs
    ):
        """Create a new Bancontact paymentType ressource.

        :param holder: The holder name.
        """
        super().__init__(**kwargs)
        self.holder: str = holder

    def serialize(self) -> dict:
        return {
            "holder": self.holder,
        }

    @classmethod
    def fromDict(cls, data: dict) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
