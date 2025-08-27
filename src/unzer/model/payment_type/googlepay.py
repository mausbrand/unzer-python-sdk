from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class Googlepay(PaymentType):
    method = PaymentTypes.GOOGLE_PAY
    method_name = PaymentMethodTypes.GOOGLE_PAY
