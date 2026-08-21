"""One class per payment method.

Seven of them take data from the server, the rest are created in the browser and
deliberately carry no fields. Which is which, and why, is in
``docs/payment-methods.md``.
"""
from .abstract_paymenttype import PaymentType
from .alipay import Alipay
from .applepay import Applepay
from .bancontact import Bancontact
from .card import Card
from .clicktopay import ClickToPay
from .eps import Eps
from .googlepay import Googlepay
from .ideal import Ideal
from .klarna import Klarna
from .openbanking_pis import OpenbankingPis
from .paylater_direct_debit import PaylaterDirectDebit
from .paylater_installment import PaylaterInstallment
from .paylater_invoice import PaylaterInvoice
from .paypal import PayPal
from .payu import PayU
from .postfinance_card import PostFinanceCard
from .postfinance_efinance import PostFinanceEfinance
from .prepayment import Prepayment
from .przelewy24 import Przelewy24
from .sepa_direct_debit import SepaDirectDebit
from .sofort import Sofort
from .twint import Twint
from .wechatpay import Wechatpay
from .wero import Wero

__all__ = [
    "Alipay",
    "Applepay",
    "Bancontact",
    "Card",
    "ClickToPay",
    "Eps",
    "Googlepay",
    "Ideal",
    "Klarna",
    "OpenbankingPis",
    "PayPal",
    "PayU",
    "PaylaterDirectDebit",
    "PaylaterInstallment",
    "PaylaterInvoice",
    "PaymentType",
    "PostFinanceCard",
    "PostFinanceEfinance",
    "Prepayment",
    "Przelewy24",
    "SepaDirectDebit",
    "Sofort",
    "Twint",
    "Wechatpay",
    "Wero",
]
