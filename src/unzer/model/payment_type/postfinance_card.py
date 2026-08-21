from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class PostFinanceCard(PaymentType):
    """PostFinance Card

    Debit card of the swiss PostFinance. Redirect payment in CHF.
    """

    method = PaymentTypes.PF_CARD
    method_name = PaymentMethodTypes.POST_FINANCE_CARD
