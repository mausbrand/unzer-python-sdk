from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class PaylaterInvoice(PaymentType):
    """Paylater Unzer Invoice

    Unzer Invoice is a part of Unzer's Buy Now Pay Later (BNPL) offering.
    """

    method = PaymentTypes.UNZER_PAYLATER_INVOICE
    method_name = PaymentMethodTypes.UNZER_INVOICE
