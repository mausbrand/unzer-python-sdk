from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Card(PaymentType):
    """Credit or debit card.

    Deliberately without card fields: accepting raw card data would put the integration
    under PCI-DSS obligations. Created in the browser through the payment page or the UI
    components, so the backend only receives the resulting type id.

    .. seealso:: ``docs/payment-methods.md``
    """

    method = PaymentTypes.CARD
    method_name = PaymentMethodTypes.CARD
