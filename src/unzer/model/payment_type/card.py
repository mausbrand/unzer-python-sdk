from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Card(PaymentType):
    method = PaymentTypes.CARD
    method_name = PaymentMethodTypes.CARD
