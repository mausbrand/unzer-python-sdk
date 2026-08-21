import typing as t

from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Bancontact(PaymentType):
    """Bancontact.

    Takes an optional card holder; everything else the customer enters at the
    redirect.

    .. seealso:: ``docs/payment-methods.md``
    """

    method = PaymentTypes.BANCONTACT
    method_name = PaymentMethodTypes.BANCONTACT

    REQUIRED_ATTRIBUTES: t.ClassVar[list[str]] = ["holder"]

    def __init__(
            self,
            holder: str | None = None,
            **kwargs
    ):
        """Create a new Bancontact paymentType ressource.

        :param holder: The holder name.
        """
        super().__init__(**kwargs)
        self.holder: str | None = holder

    def serialize(self) -> dict:
        if not self.holder:
            return super().serialize()

        return {
            "holder": self.holder,
        }

    @classmethod
    def fromDict(cls, data: dict) -> t.Self:
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
