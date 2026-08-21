import typing as t

from unzer.model.base import JSONValue
from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Wero(PaymentType):
    """Wero

    European wallet for instant payments via smartphone. Charge only, requires a redirect.
    """

    method = PaymentTypes.WERO
    method_name = PaymentMethodTypes.WERO

    def __init__(
            self,
            key: str = None,
            walletId: str = None,
            **kwargs,
    ):
        """Create a new Wero paymentType resource.

        :param key: (optional) (original: id) ID for this payment type
        :param walletId: (optional) Id of the customer's Wero wallet.
        """
        super().__init__(key=key, **kwargs)
        self.walletId = walletId

    def serialize(self) -> dict[str, JSONValue]:
        # Only send what is set: an empty body is valid, a null value is not
        return {key: value for key, value in (("walletId", self.walletId),) if value is not None}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
