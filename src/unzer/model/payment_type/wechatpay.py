from unzer.model.payment import PaymentMethodTypes, PaymentTypes

from .abstract_paymenttype import PaymentType


class Wechatpay(PaymentType):
    """WeChat Pay

    Wallet of the chinese provider WeChat, available in most European countries.
    Requires a redirect to the wallet.
    """

    method = PaymentTypes.WECHATPAY
    method_name = PaymentMethodTypes.WECHATPAY
