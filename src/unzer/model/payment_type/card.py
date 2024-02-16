from unzer.model.payment import PaymentTypes
from .abstract_paymenttype import PaymentType


class Card(PaymentType):
    method = PaymentTypes.CARD
