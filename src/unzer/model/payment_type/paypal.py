__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

from .abstract_paymenttype import PaymentType
from unzer.model.payment import PaymentTypes


class PayPal(PaymentType):
    method = PaymentTypes.PAYPAL
