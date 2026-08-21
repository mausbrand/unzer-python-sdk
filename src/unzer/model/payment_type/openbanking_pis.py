import typing as t

from unzer.model.base import JSONValue
from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class OpenbankingPis(PaymentType):
    """Unzer Open Banking PIS, marketed as *Unzer Direct Bank Transfer*

    Pay-by-bank based on a payment initiation service (PIS): the customer is redirected
    to log into their own online banking and authorizes the transfer there.
    Unzer builds this on Mastercard's open banking platform.
    Available in Germany and Austria in EUR, and replaces Sofort.

    Charge only. Note that the charge stays *pending* after the customer returns:
    it only turns into *success* once the transfer is actually settled, which takes
    one up to seven business days.

    Named ``OpenbankingPis`` in the PHP SDK and ``OpenBanking`` in the Java SDK.
    """

    method = PaymentTypes.OPEN_BANKING
    method_name = PaymentMethodTypes.DIRECT_BANK_TRANSFER

    def __init__(
            self,
            key: str | None = None,
            ibanCountry: str | None = None,
            **kwargs,
    ):
        """Create a new Direct Bank Transfer paymentType resource.

        :param key: (optional) (original: id) ID for this payment type
        :param ibanCountry: (optional) Country of the customer's bank account
            in ISO 3166 ALPHA-2 format (e.g. ``DE``).
        """
        super().__init__(key=key, **kwargs)
        self.ibanCountry = ibanCountry

    def serialize(self) -> dict[str, JSONValue]:
        # Only send what is set: an empty body is valid, a null value is not
        return {key: value for key, value in (("ibanCountry", self.ibanCountry),) if value is not None}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
