from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class PayU(PaymentType):
    """PayU

    Redirect payment for Poland and the Czech Republic (PLN and CZK).
    """

    method = PaymentTypes.PAYU
    method_name = PaymentMethodTypes.PAYU
