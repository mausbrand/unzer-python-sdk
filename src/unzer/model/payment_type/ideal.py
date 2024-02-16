__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

from unzer.model.payment import PaymentTypes
from .abstract_paymenttype import PaymentType


class Ideal(PaymentType):
    method = PaymentTypes.IDEAL
