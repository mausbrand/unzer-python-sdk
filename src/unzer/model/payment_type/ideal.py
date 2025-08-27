from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class Ideal(PaymentType):
    method = PaymentTypes.IDEAL
    method_name = PaymentMethodTypes.IDEAL
