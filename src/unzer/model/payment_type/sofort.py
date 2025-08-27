from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class Sofort(PaymentType):
    method = PaymentTypes.SOFORT
    method_name = PaymentMethodTypes.SOFORT
