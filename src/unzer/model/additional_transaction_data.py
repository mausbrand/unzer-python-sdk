import enum
import logging
import typing as t
from datetime import date, datetime as dt

from unzer.model.base import BaseModel, JSONValue

logger = logging.getLogger("unzer-sdk").getChild(__name__)


class CardTransactionData(BaseModel):
    def __init__(
            self,
            recurrenceType: t.Literal["scheduled", "unscheduled", "oneclick"] = None,
            liability: t.Literal["merchant", "issuer"] = None,
            exemptionType: str = None,
            **kwargs,
    ):
        """
        Additional data for card transactions (e.g. for recurring payments, liability, exemptions).

        :param recurrenceType: Recurrence type for card payments.
            Must be either 'scheduled', 'unscheduled' or 'oneclick'.
        :param liability: Liability shift indicator (who is liable). (From API context, e.g. for 3DS liability handling.)
        :type liability: str

        :param exemptionType: Exemption type for low-value payments, etc. (Used in specific regulatory or risk contexts.)
        :type exemptionType: str
        """
        super().__init__(**kwargs)
        self.recurrenceType = recurrenceType
        self.liability = liability
        self.exemptionType = exemptionType

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "recurrenceType": self.recurrenceType,
            "liability": self.liability,
            "exemptionType": self.exemptionType,
        }
        return data

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        raise NotImplementedError


class ShippingTransactionData(BaseModel):
    def __init__(
            self,
            deliveryTrackingId: str = None,
            deliveryService: str = None,
            returnTrackingId: str = None,
            **kwargs,
    ):
        """
        Additional data related to shipping info for a transaction.

        :param deliveryTrackingId: Tracking ID from shipping from merchant to customer.
        :param deliveryService: Delivery service from shipment from merchant to customer.
        :param returnTrackingId: Tracking ID from shipping from merchant to customer.
        """
        super().__init__(**kwargs)
        self.deliveryTrackingId = deliveryTrackingId
        self.deliveryService = deliveryService
        self.returnTrackingId = returnTrackingId

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "deliveryTrackingId": self.deliveryTrackingId,
            "deliveryService": self.deliveryService,
            "returnTrackingId": self.returnTrackingId,
        }
        return data

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        raise NotImplementedError

class CustomerGroup(enum.StrEnum):
    TOP = "TOP"
    GOOD = "GOOD"
    NEUTRAL = "NEUTRAL"



class RegistrationLevel(enum.IntEnum):
    GUEST = 0
    REGISTERED = 1


class RiskData(BaseModel):
    def __init__(
            self,
            confirmedAmount: float = None,
            confirmedOrders: int = None,
            customerGroup: CustomerGroup = None,
            customerId: str = None,
            registrationDate: dt | date = None,
            registrationLevel: RegistrationLevel = None,
            threatMetrixId: str = None,
            **kwargs
    ):
        """
        Additional risk-related data for the transaction (e.g. for fraud/risk assessments).

        :param confirmedAmount: The amount/value of the successful transactions paid by the end customer.
        :param confirmedOrders: The number of successful transactions paid by the end customer.
        :param customerGroup: Customer classification for the customer.
        :param customerId: The customer ID of the customer. Unzer-format ID String: "s-cst-...".
        :param registrationDate: Customer registration date in your shop.
        :param registrationLevel: Customer registration level.
        :param threatMetrixId: The ThreatMetrix session ID (third-party fraud system ID).
        """
        super().__init__(**kwargs)
        self.threatMetrixId = threatMetrixId
        self.registrationLevel = registrationLevel
        self.registrationDate = registrationDate
        self.customerId = customerId
        self.customerGroup = customerGroup
        self.confirmedOrders = confirmedOrders
        self.confirmedAmount = confirmedAmount

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "threatMetrixId": self.threatMetrixId,
            "registrationLevel": self.registrationLevel.value if self.registrationLevel is not None else None,
            "registrationDate": (self.registrationDate.strftime("%Y%m%d")
                                 if self.registrationDate is not None else None),
            "customerId": self.customerId,
            "customerGroup": self.customerGroup.value if self.customerGroup is not None else None,
            "confirmedOrders": self.confirmedOrders,
            "confirmedAmount": self.confirmedAmount,
        }
        return data

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        raise NotImplementedError


class PaypalData(BaseModel):
    def __init__(
            self,
            checkoutType: t.Literal["EXPRESS"] = None,
            **kwargs
    ):
        """
        Additional data for PayPal transactions (especially in context of recurring or one-click behavior).

        :param checkoutType: Checkout type for PayPal transaction.
        :type checkoutType: str
        """
        super().__init__(**kwargs)
        self.checkoutType = checkoutType

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "checkoutType": self.checkoutType,
        }
        return data

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        raise NotImplementedError


class AdditionalTransactionData(BaseModel):
    def __init__(
            self,
            card: CardTransactionData = None,
            shipping: ShippingTransactionData = None,
            risk_data: RiskData = None,
            paypal: PaypalData = None,
            **kwargs
    ):
        """
        Container for all types of additional transaction data (card, shipping, risk, PayPal).

        This object can be included in authorization or charge requests to pass
        auxiliary information supported by the Unzer API
        (for example, to enable recurring payments, set shipping tracking, risk metadata, etc.).
        In the API request body, this is often under the key ``additionalTransactionData``.

        :param card: Card-specific transaction data (recurrence, liability, exemptions).
        :param shipping: Shipping-related data (tracking, service, returns).
        :param risk_data: Risk/fraud mitigation data.
        :param paypal: PayPal-specific data (checkoutType etc.).
        """
        super().__init__(**kwargs)
        self.card = card
        self.shipping = shipping
        self.risk_data = risk_data
        self.paypal = paypal

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "card": self.card.serialize() if self.card else None,
            "shipping": self.shipping.serialize() if self.shipping else None,
            "riskData": self.risk_data.serialize() if self.risk_data else None,
            "paypal": self.paypal.serialize() if self.paypal else None,
        }
        return data

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        raise NotImplementedError
