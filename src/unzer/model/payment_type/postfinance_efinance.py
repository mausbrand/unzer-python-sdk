from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class PostFinanceEfinance(PaymentType):
    """PostFinance e-finance

    Online banking of the swiss PostFinance. Redirect payment in CHF.
    """

    method = PaymentTypes.PF_EFINANCE
    method_name = PaymentMethodTypes.POST_FINANCE_EFINANCE
