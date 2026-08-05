from unzer.model.payment import PaymentMethodTypes, PaymentTypes
from .abstract_paymenttype import PaymentType


class Alipay(PaymentType):
    """Alipay

    Wallet of the chinese provider Alipay, available in several European countries.
    Requires a redirect to the wallet.
    """

    method = PaymentTypes.ALIPAY
    method_name = PaymentMethodTypes.ALI_PAY
