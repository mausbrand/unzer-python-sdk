from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class PayPal(PaymentType):
    """PayPal.

    Created in the browser through the payment page or the UI components,
    so this class carries no fields -- the backend only receives the resulting
    type id.

    .. seealso:: ``docs/payment-methods.md``
    """

    method = PaymentTypes.PAYPAL
    method_name = PaymentMethodTypes.PAYPAL
