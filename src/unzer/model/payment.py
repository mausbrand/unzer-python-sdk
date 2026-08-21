import enum
import logging
import re
import typing as t
from types import NoneType

from ..utils import parseBool, parseDateTime, roundAmount
from .additional_transaction_data import AdditionalTransactionData
from .base import BaseModel

if t.TYPE_CHECKING:
    from ..client import UnzerClient

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class TransactionStatus(enum.Enum):
    """Status of a single transaction inside a payment.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/TransactionStatus.php
    """

    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"
    RESUMED = "resumed"


class Action(enum.Enum):
    """Transaction type of a transaction inside a payment.

    Note that a payment lists every transaction it has, so anything but ``authorize``
    and ``charge`` shows up here as soon as a payment was cancelled, shipped or paid
    out -- even though this SDK cannot yet create those. Keep this complete: a
    missing member makes :meth:`UnzerClient.getPayment` raise for the whole payment.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/TransactionTypes.php
    """

    AUTHORIZE = "authorize"
    PREAUTHORIZE = "preauthorize"
    CHARGE = "charge"
    REVERSAL = "cancel-authorize"
    REFUND = "cancel-charge"
    SHIPMENT = "shipment"
    PAYOUT = "payout"
    CHARGEBACK = "chargeback"
    SCA = "strong_customer_authentication"


class PaymentState(enum.Enum):
    """Overall state of a payment.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/PaymentState.php
    """

    PENDING = 0
    COMPLETED = 1
    CANCELED = 2
    PARTLY = 3
    PAYMENT_REVIEW = 4
    CHARGEBACK = 5
    CREATE = 6


class PaymentTypes(enum.Enum):
    """
    Supported payment types

    Used as short-name in type-ids like ``s-crd-abc456def789``

    .. seealso:: https://github.com/unzerdev/java-sdk/blob/main/src/main/java/com/unzer/payment/paymenttypes/PaymentTypeEnum.java  # noqa: E501

    The official SDKs disagree on the exact set, so both were compared. Three
    deliberate differences:

    ``UNKNOWN("unknown")``
        Exists in the Java SDK, which uses it as a parsing fallback
        (``.orElse(PaymentTypeEnum.UNKNOWN)``), and not in the PHP SDK
        (``Constants/IdStrings.php``). Left out here: an unrecognised short code
        means this SDK is behind the API, and a placeholder would hide that.
        See :meth:`PaymentGetResponse.getPaymentTypeFromTypeId`.

    ``ppg`` (payment page)
        The PHP SDK counts the payment page among the payment types. It is a
        resource of its own here, and the API never puts a ``s-ppg-`` id into
        ``resources.typeId`` -- it belongs to ``resources.payPageId``, verified
        against the sandbox. See :class:`unzer.model.PaymentPage`.

    ``ctp`` (Click to Pay)
        Present here, and a constant but not a payment type in the PHP SDK.
        The method is live -- sandbox accounts have it enabled.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/IdStrings.php
    """
    CARD = "crd"
    CLICK_TO_PAY = "ctp"
    EPS = "eps"
    GIROPAY = "gro"
    GOOGLE_PAY = "gop"
    IDEAL = "idl"
    INVOICE = "ivc"
    INVOICE_GUARANTEED = "ivg"  # deprecated
    INVOICE_FACTORING = "ivf"  # deprecated
    INVOICE_SECURED = "ivs"  # deprecated
    PAYPAL = "ppl"
    PAYU = "pyu"
    PREPAYMENT = "ppy"
    PRZELEWY24 = "p24"
    SEPA_DIRECT_DEBIT = "sdd"
    SEPA_DIRECT_DEBIT_GUARANTEED = "ddg"  # deprecated
    SEPA_DIRECT_DEBIT_SECURED = "dds"  # deprecated
    SOFORT = "sft"
    PIS = "pis"
    ALIPAY = "ali"
    WECHATPAY = "wcp"
    APPLE_PAY = "apl"
    HIRE_PURCHASE_RATE_PLAN = "hdd"
    INSTALLMENT_SECURED_RATE_PLAN = "ins"  # deprecated
    BANCONTACT = "bct"
    PF_CARD = "pfc"
    PF_EFINANCE = "pfe"
    UNZER_PAYLATER_INVOICE = "piv"
    KLARNA = "kla"
    PAYLATER_INSTALLMENT = "pit"
    PAYLATER_DIRECT_DEBIT = "pdd"
    TWINT = "twt"
    OPEN_BANKING = "obp"
    WERO = "wro"


class PaymentMethodTypes(enum.Enum):
    """
    Full name of supported payment types

    Used as name in URLs like ``types/<name>/``

    .. seealso:: https://github.com/unzerdev/integration-core/blob/master/src/BusinessLogic/Domain/PaymentMethod/Enums/PaymentMethodTypes.php  # noqa: E501
    """
    ALI_PAY = "alipay"
    APPLE_PAY = "applepay"
    BANCONTACT = "bancontact"
    CARD = "card"
    GIROPAY = "giropay"
    GOOGLE_PAY = "googlepay"
    IDEAL = "ideal"
    KLARNA = "klarna"
    PAYPAL = "paypal"
    PAYU = "payu"
    PRZELEWY24 = "przelewy24"
    POST_FINANCE_CARD = "post-finance-card"
    POST_FINANCE_EFINANCE = "post-finance-efinance"
    SOFORT = "sofort"
    TWINT = "twint"
    UNZER_DIRECT_DEBIT = "sepa-direct-debit"
    DIRECT_DEBIT_SECURED = "paylater-direct-debit"
    UNZER_INSTALLMENT = "paylater-installment"
    UNZER_INVOICE = "paylater-invoice"
    UNZER_PREPAYMENT = "prepayment"
    WECHATPAY = "wechatpay"
    WERO = "wero"
    EPS = "eps"
    DIRECT_BANK_TRANSFER = "openbanking-pis"
    CLICK_TO_PAY = "clicktopay"


# TODO: Combine PaymentMethodTypes and PaymentTypes in a dataclass to have their mapping too?

paymentUrlRe = re.compile(
    # Host and version are not pinned: the endpoint is configurable, and some
    # resources answer on a newer version than the one that was requested.
    r"^https://[\w.-]+/v\d+/"
    r"(?P<operation>[a-z]+)/(?P<paymentId>[\w-]+)"  # payments/{codeOrOrderId}
    # /[charges|authorize|shipments|payouts]/{txnCode|chargeCode}
    r"((/(?P<subOperation>[a-z-]+)/(?P<subCode>[\w-]+))?"
    # /chargebacks/{code} | /cancels/{code} | /due-date-extensions/{code}
    r"(/(?P<subSubOperation>[a-z-]+)/(?P<subSubCode>[\w-]+))?)?"
)


class PaymentGetResponse(BaseModel):

    def __init__(
            self,
            paymentId=None,
            paymentType=None,
            state=None,
            currency=None,
            orderId=None,
            invoiceId=None,
            transactions=None,
            card3ds=None,
            amountTotal=None,
            amountCharged=None,
            amountCanceled=None,
            amountRemaining=None,
            customerId=None,
            basketId=None,
            metadataId=None,
            payPageId=None,
            linkPayId=None,
            typeId=None,
            **kwargs
    ):
        """Create a new PaymentGetResponse.

        :param paymentId: The id of payment (ex: s-pay-1), assigned by unzer.
        :type paymentId: str
        :param paymentType: (optional) The type of payment
        :type paymentType: PaymentTypes
        :param state: (optional) Current state of this payment
        :type state: PaymentState
        :param currency: (optional) ISO currency code
        :type currency: str
        :param orderId: (optional) Order id of the merchant application.
            This id can also be used to get payments from the api.
            The id has to be unique for the used key pair.
        :type orderId: str
        :param invoiceId: (optional) InvoiceId of the merchant.
        :type invoiceId: str
        :param transactions: (optional) List of subsequence transaction(s).
        :type transactions: list[PaymentTransaction]
        :param card3ds: (optional)
        :type card3ds: bool | None

        Amounts
        :param amountTotal: (optional) Initial amount reduced by cancellations during authorization
        :type amountTotal: float
        :param amountCharged: (optional) Already charged amount
        :type amountCharged: float
        :param amountCanceled: (optional) Refunded amount of all charges
        :type amountCanceled: float
        :param amountRemaining: (optional) Difference between total and charged
        :type amountRemaining: float

        Resources
        :param customerId: (optional) Customer id used for this transaction.
        :type customerId: str
        :param basketId: (optional) Basket ID used for this transaction.
        :type basketId: str
        :param metadataId: (optional) Meta data ID used for this transaction.
        :type metadataId: str
        :param payPageId: (optional) Payment Page Id related to this payment.
        :type payPageId: str
        :param linkPayId: (optional)
        :type linkPayId: str
        :param typeId: (optional) Id of the types Resource that is to be used for this transaction.
        :type typeId: str
        """
        super().__init__(**kwargs)
        if transactions is None:
            transactions = []
        state = PaymentState(state)
        # if state not in vars(PaymentState).values():
        #     raise TypeError("Invalid state %r" % state)
        if not isinstance(card3ds, (bool, NoneType)):
            raise TypeError("Invalid value %r for card3ds. Must be a boolean or None." % card3ds)
        self.paymentId = paymentId  # type:str
        self.paymentType = paymentType  # type:PaymentTypes
        self.state = state  # type:PaymentState
        self.currency = currency  # type: str
        self.orderId = orderId  # type: str
        self.invoiceId = invoiceId  # type: str
        self.transactions = transactions  # type: list[PaymentTransaction]
        self.card3ds = card3ds  # type: Union[bool, None]
        # Amounts
        self.amountTotal = amountTotal  # type:float
        self.amountCharged = amountCharged  # type:float
        self.amountCanceled = amountCanceled  # type:float
        self.amountRemaining = amountRemaining  # type: float
        # PaymentResponseResources
        self.customerId = customerId  # type: str
        self.paymentId = paymentId  # type: str
        self.basketId = basketId  # type: str
        self.metadataId = metadataId  # type: str
        self.payPageId = payPageId  # type: str
        self.linkPayId = linkPayId  # type: str
        self.typeId = typeId  # type: str

    def serialize(self):
        raise NotImplementedError("No serialisation for response models.")

    # noinspection PyMethodOverriding
    @classmethod
    def fromDict(cls, data, client):
        data = data.copy()
        data["paymentId"] = data["id"]
        if data["resources"].get("typeId"):
            data["paymentType"] = PaymentGetResponse.getPaymentTypeFromTypeId(data["resources"]["typeId"])
        data["state"] = int(data["state"]["id"])
        data["card3ds"] = parseBool(data["card3ds"]) if "card3ds" in data else None
        data["transactions"] = list(map(PaymentTransaction.fromDict, data["transactions"]))
        # Amounts
        data["amountTotal"] = float(data["amount"].get("total", 0))
        data["amountCharged"] = float(data["amount"].get("charged", 0))
        data["amountCanceled"] = float(data["amount"].get("canceled", 0))
        data["amountRemaining"] = float(data["amount"].get("remaining", 0))
        # Resources
        data["customerId"] = data["resources"].get("customerId") or None
        # resources.paymentId is already on top-level
        data["basketId"] = data["resources"].get("basketId") or None
        data["metadataId"] = data["resources"].get("metadataId") or None
        data["payPageId"] = data["resources"].get("payPageId") or None
        data["linkPayId"] = data["resources"].get("linkPayId") or None
        data["typeId"] = data["resources"].get("typeId") or None
        return cls(client=client, **data)

    def getChargedTransactions(self):
        """Fetch the charged transaction of this payment.

        :return:  List of charged transaction resources.
        :rtype: list[PaymentResponse]
        """
        transactions = []
        for txn in filter(lambda txn_: txn_.action == Action.CHARGE, self.transactions):
            transactions.append(self._client.getChargedTransaction(self.paymentId, txn.transactionId))
        return transactions

    @staticmethod
    def getPaymentTypeFromTypeId(typeId: str) -> PaymentTypes:
        """Derive the payment type from a type id such as ``s-crd-abc456def789``.

        A type id is built from the environment, the short code and a random part.
        An id this SDK cannot read raises: a placeholder return value would only
        move the problem into the caller, and ``unknown`` is a real value in this
        API elsewhere (see :class:`~unzer.model.customer.Salutation`), so it could
        not be told apart from one.

        :param typeId: The id of a payment type resource.
        :raises ValueError: If the id is malformed or names an unknown type.
        """
        if not typeId:
            raise ValueError(f"Invalid typeId {typeId!r}")
        parts = typeId.split("-")
        if len(parts) < 3:
            raise ValueError(f"Invalid typeId {typeId!r}: expected the form s-crd-xxx")
        try:
            return PaymentTypes(parts[1].lower())
        except ValueError:
            raise ValueError(
                f"Unknown payment type {parts[1]!r} in typeId {typeId!r}. If Unzer "
                f"added a type, it has to be added to PaymentTypes."
            ) from None

    def charge(self, amount: float) -> "PaymentResponse":
        req_kwargs = self.__dict__.copy()
        req_kwargs["paymentType"] = PaymentType.construct(self.paymentType)(self.typeId)
        req_kwargs["amount"] = amount
        req = PaymentRequest(**req_kwargs)
        return self._client.charge(req)


class PaymentTransaction(BaseModel):
    def __init__(
            self,
            paymentId=None,
            transactionId=None,
            participantId=None,
            date=None,
            action=None,
            status=None,
            url=None,
            amount=None,
            **kwargs
    ):
        """Create a new PaymentGetResponseTransaction.
        :param paymentId: Id of the payment where this transaction belongs to
        :type paymentId: str
        :param transactionId: Id of this transaction (context based to payment)
        :type transactionId: str
        :param participantId: (optional)
        :type participantId: str
        :param date: (optional)
        :type date: datetime.datetime
        :param action: (optional)
        :type action: Action
        :param status: (optional)
        :type status: TransactionStatus
        :param url: (optional)
        :type url: str
        :param amount: (optional)
        :type amount: float
        """
        super().__init__(**kwargs)
        self.paymentId = paymentId  # type:str
        self.transactionId = transactionId  # type:str
        self.participantId = participantId  # type:str
        self.date = date  # type:datetime.datetime
        self.action = action  # type:Action
        self.status = status  # type:TransactionStatus
        self.url = url  # type:str
        self.amount = amount  # type:float

    def serialize(self):
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        # A value the enums do not know means this SDK is behind the API, which is a
        # defect worth seeing. It raises rather than degrading into a placeholder.
        data["status"] = TransactionStatus(data["status"].lower())
        data["action"] = Action(data["type"].lower())
        data["date"] = parseDateTime(data["date"])
        data["amount"] = float(data["amount"])
        # And now some ugly parsing of the url, because Unzer provide no suitable parameters
        # url-example: https://api.unzer.com/v1/payments/s-pay-123456/charges/s-chg-1
        # url-example: https://api.unzer.com/v1/payments/s-pay-123456/charges/s-chg-1/cancels/s-cnl-1
        if not data.get("url"):
            raise ValueError("Transaction has no url to derive its ids from")
        match = re.match(paymentUrlRe, data["url"])
        if not match:
            raise ValueError(f"Cannot parse transaction url {data['url']!r}")
        matchDict = match.groupdict()
        logger.debug(f"matchDict: {matchDict!r} for url {data['url']!r}")
        if matchDict["operation"] != "payments":
            raise ValueError(
                f"Unexpected operation {matchDict['operation']!r} in transaction url"
            )
        data["paymentId"] = matchDict["paymentId"]
        data["subOperation"] = matchDict["subOperation"]
        data["subCode"] = data["transactionId"] = matchDict["subCode"]
        data["subSubOperation"] = matchDict["subSubOperation"]
        data["subSubCode"] = matchDict["subSubCode"]
        return cls(**data)


class PaymentRequest(BaseModel):
    REQUIRED_ATTRIBUTES = ["paymentType"]

    def __init__(
            self,
            paymentType=None,
            paymentId=None,
            amount=None,
            currency="EUR",
            returnUrl=None,
            card3ds=None,
            paymentReference=None,
            orderId=None,
            invoiceId=None,
            effectiveInterestRate=None,
            customerId=None,
            metadataId=None,
            basketId=None,
            additional_transaction_data: AdditionalTransactionData | None = None,

            **kwargs
    ):
        """Create a new PaymentRequest.

        :param paymentType: The PaymentType model, will provide the typeId.
        :type paymentType: PaymentType
        :param amount: The amount to be charged on the specified paymentType.
            Amount in positive decimal values. Accepted length: Decimal{10,4}.
        :type amount: float
        :param currency: (optional) ISO currency code.
        :type currency: str
        :param returnUrl: (optional) URL to redirect the customer after
            the payment is completed (in case of redirect payments
            e.g. Paypal, Sofort). Required in condition.
        :type returnUrl: str
        :param card3ds: (optional) Indicate a 3ds transaction.
            Only valid for Card method: Overrides the existing
            credit card configuration if possible.
        :type card3ds: bool
        :param paymentReference: Transaction description
        :type paymentReference: str
        :param orderId: (optional) Order id that identifies the payment on merchant side.
        :type orderId: str
        :param invoiceId: (optional) invoice id that is assigned to the payment on merchant side.
        :type invoiceId: str
        :param effectiveInterestRate: (optional) Only valid for Installment method:
            The affected installment rated. Required in case of Installment method.
        :type effectiveInterestRate: str

        Resources
        :param customerId: (optional) Customer id used for this transaction.
        :type customerId: str
        :param metadataId: (optional) Meta data ID used for this transaction.
        :type metadataId: str
        :param basketId: (optional) Basket ID used for this transaction.
        :type basketId: str

        :param additional_transaction_data: (optional) Additional transaction data
        """
        super().__init__(**kwargs)
        if not isinstance(card3ds, (bool, NoneType)):
            raise TypeError("Invalid value %r for card3ds. Must be a boolean or None." % card3ds)
        self.paymentType = paymentType  # type:PaymentType
        self.paymentId = paymentId  # type:str
        self.amount = amount  # type:float
        self.currency = currency  # type: str
        self.returnUrl = returnUrl  # type: str
        self.card3ds = card3ds  # type: Union[bool, None]
        self.paymentReference = paymentReference  # type: str
        self.orderId = orderId  # type: str
        self.invoiceId = invoiceId  # type: str
        self.effectiveInterestRate = effectiveInterestRate  # type: str
        # PaymentResponseResources
        self.customerId = customerId  # type: str
        self.metadataId = metadataId  # type: str
        self.basketId = basketId  # type: str
        self.additional_transaction_data = additional_transaction_data

    def serialize(self):
        data = {
            "amount": roundAmount(self.amount),
            "currency": self.currency,
            "returnUrl": self.returnUrl,
            "card3ds": self.card3ds,
            "paymentReference": self.paymentReference,
            "orderId": self.orderId,
            "invoiceId": self.invoiceId,
            "effectiveInterestRate": self.effectiveInterestRate,
            "resources": {
                "customerId": self.customerId,
                "typeId": self.paymentType.key if self.paymentType else None,
                "metadataId": self.metadataId,
                "basketId": self.basketId,
            },
        }
        if self.additional_transaction_data is not None:
            data["additionalTransactionData"] = self.additional_transaction_data.serialize()
        return data

    @classmethod
    def fromDict(cls, data):
        raise NotImplementedError("Use PaymentResponse.fromDict for your responses.")


class PaymentResponse(BaseModel):
    def __init__(
            self,
            transactionId=None,
            isSuccess=None,
            isPending=None,
            isError=None,
            card3ds=None,
            redirectUrl=None,
            messageCode=None,
            messageMerchant=None,
            messageCustomer=None,
            amount=None,
            effectiveInterestRate=None,
            currency=None,
            returnUrl=None,
            date=None,
            customerId=None,
            paymentId=None,
            basketId=None,
            metadataId=None,
            payPageId=None,
            linkPayId=None,
            typeId=None,
            orderId=None,
            invoiceId=None,
            paymentReference=None,
            processing=None,
            **kwargs
    ):
        """Create a new PaymentResponse.

        :param transactionId: Id of this charge transaction
        :type transactionId: str
        :param isSuccess: (optional)
        :type isSuccess: bool
        :param isPending: (optional)
        :type isPending: bool
        :param isError: (optional)
        :type isError: bool
        :param card3ds: (optional) Indicate a 3ds transaction (card payment type only).
        :type card3ds: bool
        :param redirectUrl: (optional)  Some payment methods require the customer
            to leave the merchant application.
            This URL is used to bring the customer back to your application.
        :type redirectUrl: str
        :param messageCode: (optional) Response message of payment Core. Code of the message.
        :type messageCode: str
        :param messageMerchant: (optional) Response message of payment Core. Message for merchant.
        :type messageMerchant: str
        :param messageCustomer: (optional) Response message of payment Core. Message for customer.
        :type messageCustomer: str
        :param amount: (optional) The amount to be authorized on the specified account.
            The amount is rounded depending on the respective currency.
        :type amount: float
        :param effectiveInterestRate: (optional) Only valid for Installment method:
            The affected installment rated. Required in case of Installment method.
        :type effectiveInterestRate: str
        :param currency: (optional) ISO currency code.
        :type currency: str
        :param returnUrl: (optional) If customer's confirmation is required, a redirect URL will be return.
            Customer needs to be redirected to this URL and proceed the confirmation.
        :type returnUrl: str
        :param date: (optional) Timestamp of this transaction.
        :type date: datetime.datetime

        Resources
        :param customerId: (optional) Customer id used for this transaction.
        :type customerId: str
        :param paymentId: (optional) Id of the payment.
        :type paymentId: str
        :param basketId: (optional) Basket ID used for this transaction.
        :type basketId: str
        :param metadataId: (optional) Meta data ID used for this transaction.
        :type metadataId: str
        :param payPageId: (optional) Payment Page Id related to this payment.
        :type payPageId: str
        :param linkPayId: (optional)
        :type linkPayId: str
        :param typeId: (optional) Id of the types Resource that is to be used for this transaction.
        :type typeId: str

        :param orderId: (optional) Order id that identifies the payment on merchant side.
        :type orderId: str
        :param invoiceId: (optional) invoice id that is assigned to the payment on merchant side.
        :type invoiceId: str
        :param paymentReference: (optional) Transaction description.
        :type paymentReference: str
        :param processing: (optional)
        :type processing: PaymentResponseMetadata
        """
        super().__init__(**kwargs)
        self.transactionId = transactionId  # type:str
        self.isSuccess = isSuccess  # type:bool
        self.isPending = isPending  # type:bool
        self.isError = isError  # type:bool
        self.card3ds = card3ds  # type:bool
        self.redirectUrl = redirectUrl  # type:str
        self.messageCode = messageCode  # type:str
        self.messageMerchant = messageMerchant  # type:str
        self.messageCustomer = messageCustomer  # type:str
        self.amount = amount  # type:float
        self.effectiveInterestRate = effectiveInterestRate  # type:str
        self.currency = currency  # type:str
        self.returnUrl = returnUrl  # type:str
        self.date = date  # type:datetime.datetime
        self.customerId = customerId  # type:str
        self.paymentId = paymentId  # type:str
        self.basketId = basketId  # type:str
        self.metadataId = metadataId  # type:str
        self.payPageId = payPageId  # type:str
        self.linkPayId = linkPayId  # type:str
        self.typeId = typeId  # type:str
        self.orderId = orderId  # type:str
        self.invoiceId = invoiceId  # type:str
        self.paymentReference = paymentReference  # type:str
        self.processing = processing  # type:PaymentResponseMetadata

    def serialize(self):
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data: dict, client: "UnzerClient") -> t.Self:
        data = data.copy()
        data["transactionId"] = data["id"]
        data["isSuccess"] = parseBool(data["isSuccess"])
        data["isPending"] = parseBool(data["isPending"])
        data["isError"] = parseBool(data["isError"])
        data["card3ds"] = parseBool(data["card3ds"]) if "card3ds" in data else None
        data["amount"] = float(data["amount"])
        data["date"] = parseDateTime(data["date"])
        data["processing"] = PaymentResponseMetadata.fromDict(data["processing"])
        # Message
        if not data["message"]:
            data["message"] = {}
        data["messageCode"] = data["message"].get("code")
        data["messageMerchant"] = data["message"].get("merchant")
        data["messageCustomer"] = data["message"].get("customer")
        # Resources
        data["customerId"] = data["resources"].get("customerId") or None
        data["paymentId"] = data["resources"].get("paymentId") or None
        data["basketId"] = data["resources"].get("basketId") or None
        data["metadataId"] = data["resources"].get("metadataId") or None
        data["payPageId"] = data["resources"].get("payPageId") or None
        data["linkPayId"] = data["resources"].get("linkPayId") or None
        data["typeId"] = data["resources"].get("typeId") or None
        return cls(**data, client=client)

    def charge(self, amount: float) -> "PaymentResponse":
        req_kwargs = self.__dict__.copy()
        paymentTypeName = PaymentGetResponse.getPaymentTypeFromTypeId(self.typeId)
        req_kwargs["paymentType"] = PaymentType.construct(paymentTypeName)(self.typeId)
        req_kwargs["amount"] = amount
        req = PaymentRequest(**req_kwargs)
        return self._client.charge(req)


class PaymentResponseMetadata(BaseModel):
    def __init__(
            self,
            creatorId=None,
            identification=None,
            iban=None,
            bic=None,
            bank=None,
            externalOrderId=None,
            zgReferenceId=None,
            traceId=None,
            basketId=None,
            uniqueId=None,
            shortId=None,
            descriptor=None,
            holder=None,
            PDFLink=None,
            paypalBuyerId=None,
            threeDsEci=None,
            participantId=None,
            **kwargs
    ):
        """Create a new PaymentResponseMetadata.

        :param creatorId: (optional) String This value returns your creditor id.
        :type creatorId: str
        :param identification: (optional) String This value returns the descriptor for invoice and prepayment.
        :type identification: str
        :param iban: (optional) String Iban of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer Iban.
        :type iban: str
        :param bic: (optional) String Bic of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer Bic.
        :type bic: str
        :param bank: (optional)
            Bank of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer Bank.
        :type bank: str
        :param externalOrderId: (optional) String External Order Id of installment transaction
            e.g: Hirepurchase, Installment-Secured.
        :type externalOrderId: str
        :param zgReferenceId: (optional) String Reference Id of installment transaction
            e.g: Hirepurchase, Installment-Secured.
        :type zgReferenceId: str
        :param traceId: (optional)
        :type traceId: str
        :param basketId: (optional) String Basket ID used for this transaction.
        :type basketId: str
        :param uniqueId: (optional) String Unique id of the payment system used.
        :type uniqueId: str
        :param shortId: (optional) String User-friendly reference id of the payment system.
        :type shortId: str
        :param descriptor: (optional) String Descriptor of the merchant for prepayment or invoice..
        :type descriptor: str
        :param holder: (optional) String Holder of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer holder.
        :type holder: str
        :param PDFLink: (optional) String PDFLink of installment transaction
            e.g: Hirepurchase, Installment-Secured.
        :type PDFLink: str
        :param paypalBuyerId: (optional) String Id of buyer for Paypal transaction.
        :type paypalBuyerId: str
        :param threeDsEci: (optional) String 3dsEci flag from Payment Core.
        :type threeDsEci: str
        :param participantId: String Only valid for marketplace payment:
            Channel Id(s) of marketplace's participant(s).
        :type participantId: str
        """
        super().__init__(**kwargs)
        self.creatorId = creatorId  # type:str
        self.identification = identification  # type:str
        self.iban = iban  # type:str
        self.bic = bic  # type:str
        self.bank = bank  # type:str
        self.externalOrderId = externalOrderId  # type:str
        self.zgReferenceId = zgReferenceId  # type:str
        self.traceId = traceId  # type:str
        self.basketId = basketId  # type:str
        self.uniqueId = uniqueId  # type:str
        self.shortId = shortId  # type:str
        self.descriptor = descriptor  # type:str
        self.holder = holder  # type:str
        self.PDFLink = PDFLink  # type:str
        self.paypalBuyerId = paypalBuyerId  # type:str
        self.threeDsEci = threeDsEci  # type:str
        self.participantId = participantId  # type:str

    def serialize(self):
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        # Nobody, really nobody starts identifier with a digit. Unzer: here you have the 3dsEci flag
        data["threeDsEci"] = data["3dsEci"] if "3dsEci" in data else None
        return cls(**data)


from unzer.model.payment_type.abstract_paymenttype import PaymentType  # noqa: Avoid circular imports
