# -*- coding: utf-8 -*-

__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

import datetime
import logging
import re
from types import NoneType

import unzer.client
from .abstract_paymenttype import PaymentType
from .base import BaseModel
from ..utils import parseBool, parseDateTime


class TransactionStatus:
    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"


TransactionStatusInverted = {v: k for k, v in vars(TransactionStatus).items()}


class Action:
    CHARGE = "charge"
    AUTHORIZE = "authorize"


ActionInverted = {v: k for k, v in vars(Action).items()}


class PaymentState:
    PENDING = 0
    COMPLETED = 1
    CANCELED = 2
    PARTLY = 3
    PAYMENT_REVIEW = 4
    CHARGEBACK = 5
    CREATE = 6


PaymentStateInverted = {v: k for k, v in vars(PaymentState).items()}


class PaymentTypes:
    CARD = "crd"
    EPS = "eps"
    GIROPAY = "gro"
    IDEAL = "idl"
    INVOICE = "ivc"
    INVOICE_GUARANTEED = "ivg"  # deprecated
    INVOICE_FACTORING = "ivf"  # deprecated
    INVOICE_SECURED = "ivs"  # deprecated
    PAYPAL = "ppl"
    PREPAYMENT = "ppy"
    PRZELEWY24 = "p24"
    SEPA_DIRECT_DEBIT = "sdd"
    SEPA_DIRECT_DEBIT_GUARANTEED = "ddg"
    SEPA_DIRECT_DEBIT_SECURED = "dds"
    SOFORT = "sft"
    PIS = "pis"
    ALIPAY = "ali"
    WECHATPAY = "wcp"
    APPLEPAY = "apl"
    HIRE_PURCHASE_RATE_PLAN = "hdd"
    INSTALLMENT_SECURED_RATE_PLAN = "ins"
    BANCONTACT = "bct"
    PF_CARD = "pfc"
    PF_EFINANCE = "pfe"
    UNZER_PAYLATER_INVOICE = "piv"
    KLARNA = "kla"
    UNKNOWN = "unknown"


PaymentTypesInverted = {v: k for k, v in vars(PaymentTypes).items()}

paymentUrlRe = re.compile(
    r"^https://api.unzer.com/v1/"
    r"(?P<operation>[a-z]+)/(?P<paymentId>[\w-]+)"  # payments/{codeOrOrderId}
    r"((/(?P<subOperation>[a-z]+)/(?P<subCode>[\w-]+))?"  # /[charges|authorize|shipments|payouts]/{txnCode|chargeCode}
    r"(/(?P<subSubOperation>[a-z]+)/(?P<subSubCode>[\w-]+))?)?"  # /chargebacks/{chargeBackCode} | /cancels/{cancelCode}
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

            client=None,

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

        :param client: (optional) The client instance.
        :type client: unzer.client.UnzerClient
        """
        if transactions is None:
            transactions = []
        if state not in vars(PaymentState).values():
            raise TypeError("Invalid state %r" % state)
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

        self._client = client  # type: unzer.client.UnzerClient

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
    def getPaymentTypeFromTypeId(typeId):
        if not typeId:
            raise ValueError("Invalid typeId %r" % typeId)  # TODO: or return PaymentTypes.UNKNOWN?
        paymentType = typeId.split("-")[1].lower()
        if paymentType not in vars(PaymentTypes).values():
            raise ValueError("Invalid type %r" % typeId)  # TODO: or return PaymentTypes.UNKNOWN?
        return paymentType


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
        :param String:
        :param action: (optional)
        :type action: Action
        :param status: (optional)
        :type status: TransactionStatus
        :param url: (optional)
        :type url: str
        :param amount: (optional)
        :type amount: float
        """
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
        data["status"] = data["status"].lower()  # must be equivalent to enum *TransactionStatus*
        data["action"] = data["type"].lower()  # must be equivalent to enum *Action*
        data["date"] = parseDateTime(data["date"])
        data["amount"] = float(data["amount"])
        # And now some ugly parsing of the url, because Unzer provide no suitable parameters
        # url-example: https://api.unzer.com/v1/payments/s-pay-123456/charges/s-chg-1
        # url-example: https://api.unzer.com/v1/payments/s-pay-123456/charges/s-chg-1/cancels/s-cnl-1
        assert data["url"], data["url"]
        match = re.match(paymentUrlRe, data["url"])
        assert match, "Cannot match %r" % data["url"]
        matchDict = match.groupdict()
        logging.debug("matchDict: %r for url %r", matchDict, data["url"])
        assert matchDict["operation"] == "payments", "Operation %r not matching" % matchDict["operation"]
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

            client=None,
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

        :param client: (optional) The client instance.
        :type client: unzer.client.UnzerClient
        """
        if not isinstance(card3ds, (bool, NoneType)):
            raise TypeError("Invalid value %r for card3ds. Must be a boolean or None." % card3ds)
        self.paymentType = paymentType  # type:PaymentType
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

        self._client = client  # type: unzer.client.UnzerClient

    def serialize(self):
        data = {
            "amount": self.amount,
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
    def fromDict(cls, data):
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
        return cls(**data)


class PaymentResponseMetadata(BaseModel):
    def __init__(
            self,
            creatorId=None,
            identification=None,
            iban=None,
            bic=None,
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
        :param descriptor: (optional) String Descriptor of the merchant for prepayment or invoice.
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
        self.creatorId = creatorId  # type:str
        self.identification = identification  # type:str
        self.iban = iban  # type:str
        self.bic = bic  # type:str
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
