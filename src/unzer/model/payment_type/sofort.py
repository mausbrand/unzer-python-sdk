from unzer.model.payment import PaymentTypes
from .abstract_paymenttype import PaymentType


class Sofort(PaymentType):
    method = PaymentTypes.SOFORT
