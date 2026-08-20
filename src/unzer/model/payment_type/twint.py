from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class Twint(PaymentType):
    """TWINT

    Swiss smartphone payment. Redirect payment in CHF.
    """

    method = PaymentTypes.TWINT
    method_name = PaymentMethodTypes.TWINT
