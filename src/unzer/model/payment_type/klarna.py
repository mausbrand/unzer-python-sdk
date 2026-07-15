from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class Klarna(PaymentType):
    method = PaymentTypes.KLARNA
    method_name = PaymentMethodTypes.KLARNA
