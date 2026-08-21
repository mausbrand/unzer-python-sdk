from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class ClickToPay(PaymentType):
    """Click to Pay

    Card payments with a Click to Pay wallet.

    The API reference documents no ``types/clicktopay`` endpoint;
    the resource name is taken from the PHP SDK (``Clicktopay``).
    """

    method = PaymentTypes.CLICK_TO_PAY
    method_name = PaymentMethodTypes.CLICK_TO_PAY
