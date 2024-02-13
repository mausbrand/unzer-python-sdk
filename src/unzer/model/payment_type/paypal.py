__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

from .abstract_paymenttype import PaymentType


class PayPal(PaymentType):
    method = "paypal"
