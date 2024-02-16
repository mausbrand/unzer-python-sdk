from unzer.model.payment import PaymentTypes
from .abstract_paymenttype import PaymentType


class PayPal(PaymentType):
    method = PaymentTypes.PAYPAL
