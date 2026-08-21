from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Klarna(PaymentType):
    """Klarna.

    Cannot be charged directly: authorise first, then charge once the customer returns from
    the redirect. Created in the browser through the payment page or the UI components, so
    this class carries no fields.

    .. seealso:: ``docs/payment-methods.md``
    """

    method = PaymentTypes.KLARNA
    method_name = PaymentMethodTypes.KLARNA
