from unzer.model.payment import PaymentTypes
from .abstract_paymenttype import PaymentType


class Ideal(PaymentType):
    method = PaymentTypes.IDEAL
