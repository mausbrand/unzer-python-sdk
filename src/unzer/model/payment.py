"""Payments, their transactions, and the enums describing both.

A payment is the umbrella over one order: its state, its amounts, and the list of
transactions it accumulated. Note that the list contains every transaction the
payment has, including kinds this SDK cannot create.
"""
import enum
import logging
import re
import typing as t
from datetime import datetime as dt
from types import NoneType

from ..utils import parseBool, parseDateTime, roundAmount
from .additional_transaction_data import AdditionalTransactionData
from .base import BaseModel

if t.TYPE_CHECKING:
    from ..client import UnzerClient

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class TransactionStatus(enum.StrEnum):
    """Status of a single transaction inside a payment.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/TransactionStatus.php
    """

    SUCCESS = "success"
    PENDING = "pending"
    ERROR = "error"
    RESUMED = "resumed"


class Action(enum.StrEnum):
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


class PaymentState(enum.IntEnum):
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


class PaymentTypes(enum.StrEnum):
    """
    Supported payment types

    Used as short-name in type-ids like ``s-crd-abc456def789``

    .. seealso:: `PaymentTypeEnum.java
        <https://github.com/unzerdev/java-sdk/blob/main/src/main/java/com/unzer/payment/paymenttypes/PaymentTypeEnum.java>`_

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


class PaymentMethodTypes(enum.StrEnum):
    """
    Full name of supported payment types

    Used as name in URLs like ``types/<name>/``

    .. seealso:: `PaymentMethodTypes.php
        <https://github.com/unzerdev/integration-core/blob/master/src/BusinessLogic/Domain/PaymentMethod/Enums/PaymentMethodTypes.php>`_
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
    """A payment, as returned by :meth:`~unzer.UnzerClient.getPayment`.

    The payment is the umbrella over everything that happened to one order: its
    :attr:`state`, the amounts, the ids of the resources involved, and every
    :class:`PaymentTransaction` it holds. That list is the reason
    :class:`Action` has to know transaction types this SDK cannot create -- a
    payment that was cancelled elsewhere still reads back here.

    :attr:`amountTotal` is the authorised amount minus cancellations,
    :attr:`amountCharged` what was actually captured, and
    :attr:`amountRemaining` the difference. Treat anything but
    :attr:`~PaymentState.COMPLETED` as not paid.
    """

    def __init__(
            self,
            paymentId: str | None = None,
            paymentType: PaymentTypes | None = None,
            state: PaymentState | int | None = None,
            currency: str | None = None,
            orderId: str | None = None,
            invoiceId: str | None = None,
            transactions: list["PaymentTransaction"] | None = None,
            card3ds: bool | None = None,
            amountTotal: float | None = None,
            amountCharged: float | None = None,
            amountCanceled: float | None = None,
            amountRemaining: float | None = None,
            customerId: str | None = None,
            basketId: str | None = None,
            metadataId: str | None = None,
            payPageId: str | None = None,
            linkPayId: str | None = None,
            typeId: str | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new PaymentGetResponse.

        :param paymentId: The id of payment (ex: s-pay-1), assigned by unzer.
        :param paymentType: (optional) The type of payment
        :param state: (optional) Current state of this payment
        :param currency: (optional) ISO currency code
        :param orderId: (optional) Order id of the merchant application.
            This id can also be used to get payments from the api.
            The id has to be unique for the used key pair.
        :param invoiceId: (optional) InvoiceId of the merchant.
        :param transactions: (optional) List of subsequence transaction(s).
        :param card3ds: (optional)

        Amounts
        :param amountTotal: (optional) Initial amount reduced by cancellations during authorization
        :param amountCharged: (optional) Already charged amount
        :param amountCanceled: (optional) Refunded amount of all charges
        :param amountRemaining: (optional) Difference between total and charged

        Resources
        :param customerId: (optional) Customer id used for this transaction.
        :param basketId: (optional) Basket ID used for this transaction.
        :param metadataId: (optional) Meta data ID used for this transaction.
        :param payPageId: (optional) Payment Page Id related to this payment.
        :param linkPayId: (optional)
        :param typeId: (optional) Id of the types Resource that is to be used for this transaction.
        """
        super().__init__(**kwargs)
        if transactions is None:
            transactions = []
        # TODO: state defaults to None, which PaymentState() rejects -- make it required or handle None.
        state = PaymentState(state)  # type: ignore[arg-type]
        # if state not in vars(PaymentState).values():
        #     raise TypeError("Invalid state %r" % state)
        if not isinstance(card3ds, (bool, NoneType)):
            raise TypeError(f"Invalid value {card3ds!r} for card3ds. Must be a boolean or None.")
        self.paymentId: str | None = paymentId
        self.paymentType: PaymentTypes | None = paymentType
        self.state: PaymentState = state
        self.currency: str | None = currency
        self.orderId: str | None = orderId
        self.invoiceId: str | None = invoiceId
        self.transactions: list[PaymentTransaction] = transactions
        self.card3ds: bool | None = card3ds
        # Amounts
        self.amountTotal: float | None = amountTotal
        self.amountCharged: float | None = amountCharged
        self.amountCanceled: float | None = amountCanceled
        self.amountRemaining: float | None = amountRemaining
        # PaymentResponseResources
        self.customerId: str | None = customerId
        self.paymentId = paymentId
        self.basketId: str | None = basketId
        self.metadataId: str | None = metadataId
        self.payPageId: str | None = payPageId
        self.linkPayId: str | None = linkPayId
        self.typeId: str | None = typeId

    def serialize(self) -> dict[str, t.Any]:
        raise NotImplementedError("No serialisation for response models.")

    # noinspection PyMethodOverriding
    # TODO: Requires a client, which BaseModel.fromDict does not have -- violates the base signature.
    @classmethod
    def fromDict(  # type: ignore[override]
            cls,
            data: dict[str, t.Any],
            client: "UnzerClient",
    ) -> t.Self:
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

    def getChargedTransactions(self) -> list["PaymentResponse"]:
        """Fetch the charged transaction of this payment.

        :return:  List of charged transaction resources.
        """
        transactions = []
        for txn in filter(lambda txn_: txn_.action == Action.CHARGE, self.transactions):
            # TODO: Fails on None, with no client or no paymentId.
            transactions.append(
                self._client.getChargedTransaction(  # type: ignore[union-attr]
                    self.paymentId,  # type: ignore[arg-type]
                    txn.transactionId,
                )
            )
        return transactions

    @staticmethod
    def getPaymentTypeFromTypeId(typeId: str | None) -> PaymentTypes:
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
        """Capture an amount on this payment.

        For payment methods that are authorised first and captured later -- Klarna
        and the Pay later methods, typically on shipment. Requires the model to
        have been read through a client, since it performs a request of its own.

        :param amount: The amount to capture. Can be less than the authorised
            amount; the rest stays open.
        :return: The transaction that was created.
        """
        req_kwargs = self.__dict__.copy()
        # TODO: paymentType may be None, which construct() does not handle.
        req_kwargs["paymentType"] = PaymentType.construct(self.paymentType)(self.typeId)  # type: ignore[arg-type]
        req_kwargs["amount"] = amount
        req = PaymentRequest(**req_kwargs)
        # TODO: Fails with an AttributeError on None when the model was not read through a client.
        return self._client.charge(req)  # type: ignore[union-attr]


class PaymentTransaction(BaseModel):
    """One transaction within a payment.

    :attr:`action` says what kind it is and :attr:`status` how it went. The ids
    are parsed out of the transaction's URL, because the API does not return them
    as separate fields -- which is why :attr:`url` is required for this model to
    be readable at all.
    """

    def __init__(
            self,
            paymentId: str | None = None,
            transactionId: str | None = None,
            participantId: str | None = None,
            date: dt | None = None,
            action: Action | None = None,
            status: TransactionStatus | None = None,
            url: str | None = None,
            amount: float | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new PaymentGetResponseTransaction.
        :param paymentId: Id of the payment where this transaction belongs to
        :param transactionId: Id of this transaction (context based to payment)
        :param participantId: (optional)
        :param date: (optional)
        :param action: (optional)
        :param status: (optional)
        :param url: (optional)
        :param amount: (optional)
        """
        super().__init__(**kwargs)
        self.paymentId: str | None = paymentId
        self.transactionId: str | None = transactionId
        self.participantId: str | None = participantId
        self.date: dt | None = date
        self.action: Action | None = action
        self.status: TransactionStatus | None = status
        self.url: str | None = url
        self.amount: float | None = amount

    def serialize(self) -> dict[str, t.Any]:
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
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
    """The payload of an authorize or charge call.

    Request-only; use :class:`PaymentResponse` for what comes back. The payment
    type is the one required field -- if it has no ``key`` yet, the client creates
    it as part of the call.

    :attr:`returnUrl` is required for every payment method that sends the customer
    away, which is most of them, and for the Pay later methods it is required
    outright because their verification flow redirects.
    """

    REQUIRED_ATTRIBUTES: t.ClassVar[list[str]] = ["paymentType"]

    def __init__(
            self,
            paymentType: "PaymentType | None" = None,
            paymentId: str | None = None,
            amount: float | None = None,
            currency: str = "EUR",
            returnUrl: str | None = None,
            card3ds: bool | None = None,
            paymentReference: str | None = None,
            orderId: str | None = None,
            invoiceId: str | None = None,
            effectiveInterestRate: float | str | None = None,
            customerId: str | None = None,
            metadataId: str | None = None,
            basketId: str | None = None,
            additional_transaction_data: AdditionalTransactionData | None = None,

            **kwargs: t.Any,
    ) -> None:
        """Create a new PaymentRequest.

        :param paymentType: The PaymentType model, will provide the typeId.
        :param amount: The amount to be charged on the specified paymentType.
            Amount in positive decimal values. Accepted length: Decimal{10,4}.
        :param currency: (optional) ISO currency code.
        :param returnUrl: (optional) URL to redirect the customer after
            the payment is completed (in case of redirect payments
            e.g. Paypal, Sofort). Required in condition.
        :param card3ds: (optional) Indicate a 3ds transaction.
            Only valid for Card method: Overrides the existing
            credit card configuration if possible.
        :param paymentReference: Transaction description
        :param orderId: (optional) Order id that identifies the payment on merchant side.
        :param invoiceId: (optional) invoice id that is assigned to the payment on merchant side.
        :param effectiveInterestRate: (optional) Only valid for Installment method:
            The affected installment rated. Required in case of Installment method.

        Resources
        :param customerId: (optional) Customer id used for this transaction.
        :param metadataId: (optional) Meta data ID used for this transaction.
        :param basketId: (optional) Basket ID used for this transaction.

        :param additional_transaction_data: (optional) Additional transaction data
        """
        super().__init__(**kwargs)
        if not isinstance(card3ds, (bool, NoneType)):
            raise TypeError(f"Invalid value {card3ds!r} for card3ds. Must be a boolean or None.")
        self.paymentType: PaymentType | None = paymentType
        self.paymentId: str | None = paymentId
        self.amount: float | None = amount
        self.currency: str = currency
        self.returnUrl: str | None = returnUrl
        self.card3ds: bool | None = card3ds
        self.paymentReference: str | None = paymentReference
        self.orderId: str | None = orderId
        self.invoiceId: str | None = invoiceId
        self.effectiveInterestRate: float | str | None = effectiveInterestRate
        # PaymentResponseResources
        self.customerId: str | None = customerId
        self.metadataId: str | None = metadataId
        self.basketId: str | None = basketId
        self.additional_transaction_data: AdditionalTransactionData | None = additional_transaction_data

    def serialize(self) -> dict[str, t.Any]:
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
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
        raise NotImplementedError("Use PaymentResponse.fromDict for your responses.")


class PaymentResponse(BaseModel):
    """The result of an authorize or charge call.

    Three flags, of which exactly one is set: :attr:`isSuccess`,
    :attr:`isPending`, :attr:`isError`. Pending is not a failure -- it means the
    customer has to confirm something at :attr:`redirectUrl`, after which the
    outcome has to be fetched with :meth:`~unzer.UnzerClient.getPayment`.

    :attr:`processing` carries the reference numbers to quote in support cases,
    and for prepayment or invoice the bank details the customer has to transfer to.
    """

    def __init__(
            self,
            transactionId: str | None = None,
            isSuccess: bool | None = None,
            isPending: bool | None = None,
            isError: bool | None = None,
            card3ds: bool | None = None,
            redirectUrl: str | None = None,
            messageCode: str | None = None,
            messageMerchant: str | None = None,
            messageCustomer: str | None = None,
            amount: float | None = None,
            effectiveInterestRate: float | str | None = None,
            currency: str | None = None,
            returnUrl: str | None = None,
            date: dt | None = None,
            customerId: str | None = None,
            paymentId: str | None = None,
            basketId: str | None = None,
            metadataId: str | None = None,
            payPageId: str | None = None,
            linkPayId: str | None = None,
            typeId: str | None = None,
            orderId: str | None = None,
            invoiceId: str | None = None,
            paymentReference: str | None = None,
            processing: "PaymentResponseMetadata | None" = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new PaymentResponse.

        :param transactionId: Id of this charge transaction
        :param isSuccess: (optional)
        :param isPending: (optional)
        :param isError: (optional)
        :param card3ds: (optional) Indicate a 3ds transaction (card payment type only).
        :param redirectUrl: (optional)  Some payment methods require the customer
            to leave the merchant application.
            This URL is used to bring the customer back to your application.
        :param messageCode: (optional) Response message of payment Core. Code of the message.
        :param messageMerchant: (optional) Response message of payment Core. Message for merchant.
        :param messageCustomer: (optional) Response message of payment Core. Message for customer.
        :param amount: (optional) The amount to be authorized on the specified account.
            The amount is rounded depending on the respective currency.
        :param effectiveInterestRate: (optional) Only valid for Installment method:
            The affected installment rated. Required in case of Installment method.
        :param currency: (optional) ISO currency code.
        :param returnUrl: (optional) If customer's confirmation is required, a redirect URL will be return.
            Customer needs to be redirected to this URL and proceed the confirmation.
        :param date: (optional) Timestamp of this transaction.

        Resources
        :param customerId: (optional) Customer id used for this transaction.
        :param paymentId: (optional) Id of the payment.
        :param basketId: (optional) Basket ID used for this transaction.
        :param metadataId: (optional) Meta data ID used for this transaction.
        :param payPageId: (optional) Payment Page Id related to this payment.
        :param linkPayId: (optional)
        :param typeId: (optional) Id of the types Resource that is to be used for this transaction.

        :param orderId: (optional) Order id that identifies the payment on merchant side.
        :param invoiceId: (optional) invoice id that is assigned to the payment on merchant side.
        :param paymentReference: (optional) Transaction description.
        :param processing: (optional)
        """
        super().__init__(**kwargs)
        self.transactionId: str | None = transactionId
        self.isSuccess: bool | None = isSuccess
        self.isPending: bool | None = isPending
        self.isError: bool | None = isError
        self.card3ds: bool | None = card3ds
        self.redirectUrl: str | None = redirectUrl
        self.messageCode: str | None = messageCode
        self.messageMerchant: str | None = messageMerchant
        self.messageCustomer: str | None = messageCustomer
        self.amount: float | None = amount
        self.effectiveInterestRate: float | str | None = effectiveInterestRate
        self.currency: str | None = currency
        self.returnUrl: str | None = returnUrl
        self.date: dt | None = date
        self.customerId: str | None = customerId
        self.paymentId: str | None = paymentId
        self.basketId: str | None = basketId
        self.metadataId: str | None = metadataId
        self.payPageId: str | None = payPageId
        self.linkPayId: str | None = linkPayId
        self.typeId: str | None = typeId
        self.orderId: str | None = orderId
        self.invoiceId: str | None = invoiceId
        self.paymentReference: str | None = paymentReference
        self.processing: PaymentResponseMetadata | None = processing

    def serialize(self) -> dict[str, t.Any]:
        raise NotImplementedError("No serialisation for response models.")

    # TODO: Requires a client, which BaseModel.fromDict does not have -- violates the base signature.
    @classmethod
    def fromDict(  # type: ignore[override]
            cls,
            data: dict[str, t.Any],
            client: "UnzerClient",
    ) -> t.Self:
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
        """Capture an amount on the payment this response belongs to.

        Same as :meth:`PaymentGetResponse.charge`, so that a capture can follow
        straight on from an authorization without fetching the payment first.

        :param amount: The amount to capture.
        :return: The transaction that was created.
        """
        req_kwargs = self.__dict__.copy()
        paymentTypeName = PaymentGetResponse.getPaymentTypeFromTypeId(self.typeId)
        req_kwargs["paymentType"] = PaymentType.construct(paymentTypeName)(self.typeId)
        req_kwargs["amount"] = amount
        req = PaymentRequest(**req_kwargs)
        # TODO: Fails with an AttributeError on None when the model was not read through a client.
        return self._client.charge(req)  # type: ignore[union-attr]


class PaymentResponseMetadata(BaseModel):
    """The ``processing`` block of a payment response.

    Which of these fields are filled depends entirely on the payment method:
    :attr:`uniqueId`, :attr:`shortId` and :attr:`traceId` are always there, the
    bank details only for the methods that need them, and they can be missing
    while a verification is still outstanding.

    :attr:`shortId` is the reference a customer can read out over the phone;
    :attr:`traceId` is the one Unzer support asks for.
    """

    def __init__(
            self,
            creatorId: str | None = None,
            identification: str | None = None,
            iban: str | None = None,
            bic: str | None = None,
            bank: str | None = None,
            externalOrderId: str | None = None,
            zgReferenceId: str | None = None,
            traceId: str | None = None,
            basketId: str | None = None,
            uniqueId: str | None = None,
            shortId: str | None = None,
            descriptor: str | None = None,
            holder: str | None = None,
            PDFLink: str | None = None,
            paypalBuyerId: str | None = None,
            threeDsEci: str | None = None,
            participantId: str | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new PaymentResponseMetadata.

        :param creatorId: (optional) String This value returns your creditor id.
        :param identification: (optional) String This value returns the descriptor for invoice and prepayment.
        :param iban: (optional) String Iban of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer Iban.
        :param bic: (optional) String Bic of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer Bic.
        :param bank: (optional)
            Bank of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer Bank.
        :param externalOrderId: (optional) String External Order Id of installment transaction
            e.g: Hirepurchase, Installment-Secured.
        :param zgReferenceId: (optional) String Reference Id of installment transaction
            e.g: Hirepurchase, Installment-Secured.
        :param traceId: (optional)
        :param basketId: (optional) String Basket ID used for this transaction.
        :param uniqueId: (optional) String Unique id of the payment system used.
        :param shortId: (optional) String User-friendly reference id of the payment system.
        :param descriptor: (optional) String Descriptor of the merchant for prepayment or invoice..
        :param holder: (optional) String Holder of the merchant for prepayment or invoice.
            In the case of a direct debit, this value contains the customer holder.
        :param PDFLink: (optional) String PDFLink of installment transaction
            e.g: Hirepurchase, Installment-Secured.
        :param paypalBuyerId: (optional) String Id of buyer for Paypal transaction.
        :param threeDsEci: (optional) String 3dsEci flag from Payment Core.
        :param participantId: String Only valid for marketplace payment:
            Channel Id(s) of marketplace's participant(s).
        """
        super().__init__(**kwargs)
        self.creatorId: str | None = creatorId
        self.identification: str | None = identification
        self.iban: str | None = iban
        self.bic: str | None = bic
        self.bank: str | None = bank
        self.externalOrderId: str | None = externalOrderId
        self.zgReferenceId: str | None = zgReferenceId
        self.traceId: str | None = traceId
        self.basketId: str | None = basketId
        self.uniqueId: str | None = uniqueId
        self.shortId: str | None = shortId
        self.descriptor: str | None = descriptor
        self.holder: str | None = holder
        self.PDFLink: str | None = PDFLink
        self.paypalBuyerId: str | None = paypalBuyerId
        self.threeDsEci: str | None = threeDsEci
        self.participantId: str | None = participantId

    def serialize(self) -> dict[str, t.Any]:
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
        data = data.copy()
        # Nobody, really nobody starts identifier with a digit. Unzer: here you have the 3dsEci flag
        data["threeDsEci"] = data.get("3dsEci")
        return cls(**data)


# Imported at the end of the module to avoid a circular import.
from unzer.model.payment_type.abstract_paymenttype import PaymentType  # noqa: E402
