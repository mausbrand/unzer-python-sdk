import typing as t

from unzer.model.base import JSONValue
from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class PaylaterInstallment(PaymentType):
    """Paylater Installment

    Unzer Installment is a part of Unzer's Buy Now Pay Later (BNPL) offering, available in
    Germany, Austria and Switzerland in EUR and CHF.
    The customer pays in monthly rates of a plan selected during the checkout.

    Before this resource can be created, the available plans must be fetched with
    :meth:`unzer.UnzerClient.getPaylaterInstallmentPlans` and presented to the customer.
    The authorize call requires a customer and a basket resource
    (the basket must use the v3 schema, see :class:`unzer.model.Basket`).
    """

    method = PaymentTypes.PAYLATER_INSTALLMENT
    method_name = PaymentMethodTypes.UNZER_INSTALLMENT

    # The API reference marks only inquiryId and numberOfRates as required,
    # while the documentation claims country to be required too
    REQUIRED_ATTRIBUTES = ["inquiryId", "numberOfRates"]

    def __init__(
            self,
            key: str = None,
            inquiryId: str = None,
            numberOfRates: int = None,
            iban: str = None,
            country: str = None,
            holder: str = None,
            **kwargs,
    ):
        """Create a new Paylater Installment paymentType resource.

        :param key: (optional) (original: id) ID for this payment type
        :param inquiryId: The id of the installment plans response
            (:attr:`unzer.model.InstallmentPlans.inquiryId`, e.g. ``Tx-vyexxxzzy8p``).
        :param numberOfRates: Duration in months of the plan the customer selected.
        :param iban: (optional, but recommended) IBAN of the customer's bank account.
            Without it the customer has to transfer the monthly rates manually.
        :param country: (optional) Country of the customer's bank account
            in ISO 3166 ALPHA-2 format (e.g. ``DE``).
        :param holder: (optional, but recommended) Name of the bank account holder.
        """
        super().__init__(key=key, **kwargs)
        self.inquiryId = inquiryId
        self.numberOfRates = numberOfRates
        self.iban = iban
        self.country = country
        self.holder = holder

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "inquiryId": self.inquiryId,
            "numberOfRates": self.numberOfRates,
            "iban": self.iban,
            "country": self.country,
            "holder": self.holder,
        }
        # Only send what is set: a null value would violate the API's field constraints
        return {key: value for key, value in data.items() if value is not None}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
