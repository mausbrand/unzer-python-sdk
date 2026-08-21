import typing as t

from unzer.model.base import JSONValue
from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class PaylaterDirectDebit(PaymentType):
    """Paylater Direct Debit

    Direct Debit is a part of Unzer's Buy Now Pay Later (BNPL) offering,
    available in Germany and Austria in EUR.
    Requires a customer and a basket resource on the authorize call.
    """

    method = PaymentTypes.PAYLATER_DIRECT_DEBIT
    method_name = PaymentMethodTypes.DIRECT_DEBIT_SECURED

    REQUIRED_ATTRIBUTES = ["iban", "holder"]

    def __init__(
            self,
            key: str = None,
            iban: str = None,
            holder: str = None,
            country: str = None,
            **kwargs,
    ):
        """Create a new Paylater Direct Debit paymentType resource.

        :param key: (optional) (original: id) ID for this payment type
        :param iban: IBAN of the customer's bank account.
        :param holder: Name of the bank account holder.
        :param country: (optional) Country of the customer's bank account
            in ISO 3166 ALPHA-2 format (e.g. ``DE``).
        """
        super().__init__(key=key, **kwargs)
        self.iban = iban
        self.holder = holder
        self.country = country

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "iban": self.iban,
            "holder": self.holder,
            "country": self.country,
        }
        # Only send what is set: a null value would violate the API's field constraints
        return {key: value for key, value in data.items() if value is not None}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
