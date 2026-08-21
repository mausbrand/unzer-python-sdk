from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Przelewy24(PaymentType):
    """Przelewy24

    Polish online bank transfer. Redirect payment in PLN or EUR.
    """

    method = PaymentTypes.PRZELEWY24
    method_name = PaymentMethodTypes.PRZELEWY24
