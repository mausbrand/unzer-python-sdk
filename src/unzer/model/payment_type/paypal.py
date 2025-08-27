from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class PayPal(PaymentType):
    method = PaymentTypes.PAYPAL
    method_name = PaymentMethodTypes.PAYPAL
