from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class Applepay(PaymentType):
    method = PaymentTypes.APPLE_PAY
    method_name = PaymentMethodTypes.APPLE_PAY
