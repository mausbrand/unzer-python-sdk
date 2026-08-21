import typing as t

from unzer.model.base import JSONValue
from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class SepaDirectDebit(PaymentType):
    """SEPA Direct Debit

    The amount is collected from the customer's bank account by direct debit.
    Available in all SEPA countries in EUR.
    """

    method = PaymentTypes.SEPA_DIRECT_DEBIT
    method_name = PaymentMethodTypes.UNZER_DIRECT_DEBIT

    # The API reference marks no field as required, but the PHP SDK
    # takes the iban as the only mandatory constructor argument
    REQUIRED_ATTRIBUTES = ["iban"]

    def __init__(
            self,
            key: str = None,
            iban: str = None,
            bic: str = None,
            holder: str = None,
            **kwargs,
    ):
        """Create a new SEPA Direct Debit paymentType resource.

        :param key: (optional) (original: id) ID for this payment type
        :param iban: IBAN of the customer's bank account.
        :param bic: (optional) BIC of the customer's bank.
        :param holder: (optional) Name of the bank account holder.
            The API documentation calls this field *accountHolder*,
            but both the PHP and the Java SDK use *holder*.
        """
        super().__init__(key=key, **kwargs)
        self.iban = iban
        self.bic = bic
        self.holder = holder

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "iban": self.iban,
            "bic": self.bic,
            "holder": self.holder,
        }
        # Only send what is set: a null value would violate the API's field constraints
        return {key: value for key, value in data.items() if value is not None}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
