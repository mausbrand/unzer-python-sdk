from .base import BaseModel

# https://docs.unzer.com/reference/basic-integration-req/#allowlist-of-ip-addresses
IP_ADDRESS = {
    # Production environment
    "3.120.62.83", "18.196.35.212",
    # Sandbox environment
    "35.157.10.171", "18.197.240.190",
}


class Events:
    ALL = "all"
    AUTHORIZE = "authorize"
    AUTHORIZE_SUCCEEDED = "authorize.succeeded"
    AUTHORIZE_FAILED = "authorize.failed"
    AUTHORIZE_PENDING = "authorize.pendin"
    AUTHORIZE_EXPIRED = "authorize.expired"
    AUTHORIZE_CANCELED = "authorize.canceled"
    CHARGE = "charge"
    CHARGE_SUCCEEDED = "charge.succeeded"
    CHARGE_FAILED = "charge.failed"
    CHARGE_PENDING = "charge.pendin"
    CHARGE_EXPIRED = "charge.expired"
    CHARGE_CANCELED = "charge.canceled"
    CHARGEBACK = "chargeback"
    TYPES = "types"
    CUSTOMER = "customer"
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_DELETED = "customer.deleted"
    CUSTOMER_UPDATED = "customer.updated"
    BASKET = "basket"
    BASKET_CREATE = "basket.created"
    BASKET_UPDATED = "basket.updated"
    BASKET_USED = "basket.used"
    PAYMENT = "payment"
    PAYMENT_PENDING = "payment.pending"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_CANCELED = "payment.canceled"
    PAYMENT_PARTLY = "payment.partly"
    PAYMENT_REVIEW = "payment.payment_review"
    PAYMENT_CHARGEBACK = "payment.chargeback"
    SHIPMENT = "shipment"
    PAYOUT = "payout"
    PAYOUT_SUCCEEDED = "payout.succeeded"
    PAYOUT_FAILED = "payout.failed"


class Webhook(BaseModel):
    REQUIRED_ATTRIBUTES = [
        "event",
        "url"
    ]

    def __init__(
            self,
            url,
            event=Events.ALL,
            webhookId=None,
            **kwargs
    ):
        """Create a new Webhook.

        :param webhookId: The id of the webhook
        :type webhookId: str
        :param event: The or a list of events for this webhook
        :type event: str
        :param url: The url of the webhook
        :type url: str
        """
        super().__init__(**kwargs)
        self.webhookId = webhookId
        self.event = event
        self.url = url

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, value):
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise TypeError("Event must be a str or list of str. Got %r" % type(value))
        for val in value:
            if val not in vars(Events).values():
                raise TypeError("Invalid value %r for event" % value)
        self._event = value

    def serialize(self):
        return {
            "eventList": self.event,
            "url": self.url,
        }

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        data["webhookId"] = data["id"]
        return cls(**data)
