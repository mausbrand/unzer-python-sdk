from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Prepayment(PaymentType):
    """Unzer Prepayment

    The customer receives the bank details with the charge response and transfers the
    money before the order is shipped. The charge therefore stays *pending* until the
    payment arrives.
    """

    method = PaymentTypes.PREPAYMENT
    method_name = PaymentMethodTypes.UNZER_PREPAYMENT
