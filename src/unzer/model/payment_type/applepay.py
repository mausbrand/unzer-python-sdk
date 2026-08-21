from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Applepay(PaymentType):
    """Apple Pay.

    The payload is a signed token only the wallet can produce. Created in the browser
    through the payment page or the UI components, so this class carries no fields -- the
    backend only receives the resulting type id.

    .. seealso:: ``docs/payment-methods.md``
    """

    method = PaymentTypes.APPLE_PAY
    method_name = PaymentMethodTypes.APPLE_PAY
