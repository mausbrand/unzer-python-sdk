import typing as t

from unzer.model.base import JSONValue
from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Eps(PaymentType):
    """EPS

    Austrian online bank transfer in EUR, requires a redirect to the customer's bank.
    """

    method = PaymentTypes.EPS
    method_name = PaymentMethodTypes.EPS

    def __init__(
            self,
            key: str | None = None,
            bic: str | None = None,
            **kwargs,
    ):
        """Create a new EPS paymentType resource.

        :param key: (optional) (original: id) ID for this payment type
        :param bic: (optional) BIC of the customer's bank (e.g. ``STZZATWWXXX``).
            Can be omitted to let the customer choose the bank on the redirect page.
        """
        super().__init__(key=key, **kwargs)
        self.bic = bic

    def serialize(self) -> dict[str, JSONValue]:
        # Only send what is set: an empty body is valid, a null value is not
        return {key: value for key, value in (("bic", self.bic),) if value is not None}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
