from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Googlepay(PaymentType):
    """Google Pay.

    The payload is a signed token only the browser can produce. Created in the browser
    through the payment page or the UI components, so this class carries no fields -- the
    backend only receives the resulting type id.

    .. seealso:: ``docs/payment-methods.md``
    """

    method = PaymentTypes.GOOGLE_PAY
    method_name = PaymentMethodTypes.GOOGLE_PAY
