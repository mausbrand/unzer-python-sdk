# -*- coding: utf-8 -*-

__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

from .base import BaseModel
from .payment import Action
from ..utils import parseBool


class PaymentPage(BaseModel):
    REQUIRED_ATTRIBUTES = [
        "action",
        "amount",
        "currency",
        "returnUrl",
    ]

    def __init__(
            self,
            action=None,
            amount=None,
            currency="EUR",
            invoiceId=None,
            orderId=None,
            card3ds=None,
            returnUrl=None,
            excludeTypes=None,
            additionalAttributes=None,
            logoImage=None,
            fullPageImage=None,
            shopName=None,
            shopDescription=None,
            tagline=None,
            css=None,
            termsAndConditionUrl=None,
            privacyPolicyUrl=None,
            imprintUrl=None,
            helpUrl=None,
            contactUrl=None,
            customerId=None,
            metadataId=None,
            basketId=None,
            **kwargs
    ):
        """Create a new PaymentPage.

        Payment attributes:
        :param action: (required) Action for this paypage. Charge or authorize.
        :type action: str | Action
        :param amount: (required) The transaction amount.
        :type amount: float
        :param currency: (required) The transaction currency, in the ISO 4217 alpha-3 format.
        :type currency: str
        :param invoiceId: (optional) Your internal invoice ID.
        :type invoiceId: str
        :param orderId: (optional) A unique order ID that identifies the payment on your side.
        :type orderId: str
        :param card3ds: (optional) Switches between 3ds and non 3ds card transactions.
        :type card3ds: bool
        :param returnUrl: (required) The URL to redirect the customer to after the payment is completed.
        :type returnUrl: str
        :param excludeTypes: (optional) Exclude some of the payment types from the Payment Page.
        :type excludeTypes: list[str]
        :param additionalAttributes: (optional) Attributes for LinkPay.
        :type additionalAttributes: dict[str, str]

        Paypage config:
        :param logoImage: (optional) Your company logo to show in the Embedded Payment Page’s header.
        :type logoImage: str
        :param fullPageImage: (optional) The URL of the image to show in the Hosted Payment Page’s background.
        :type fullPageImage: str
        :param shopName: (optional) Your company name to show in the Embedded Payment Page’s header.
        :type shopName: str
        :param shopDescription: (optional) Main description of the purchase.
        :type shopDescription: str
        :param tagline: (optional) A short description to show in the Payment Page’s header.
        :type tagline: str
        :param css: (optional)
        :type css: dict[str, str]
        :param termsAndConditionUrl: (optional) Your Terms and Conditions URL to show in the Payment Page’s footer.
        :type termsAndConditionUrl: str
        :param privacyPolicyUrl: (optional) Your Privacy Policy URL to show in the Payment Page’s footer.
        :type privacyPolicyUrl: str
        :param imprintUrl: (optional) Your imprint URL to show in the Payment Page’s footer.
        :type imprintUrl: str
        :param helpUrl: (optional) The URL of the help page to show in the Payment Page’s header.
        :type helpUrl: str
        :param contactUrl: (optional) The URL of the contact page to show in the Payment Page’s header.
        :type contactUrl: str

        Resources
        :param customerId: (optional) The ID of the customers resource to be used.
        :type customerId: str
        :param metadataId: (optional) The ID of the metadata resource to be used.
        :type metadataId: str
        :param basketId: (optional) The ID of the baskets resource to be used.
        :type basketId: str
        """
        if excludeTypes is None:
            excludeTypes = []
        if additionalAttributes is None:
            additionalAttributes = {}
        if css is None:
            css = {}
        if action not in {Action.CHARGE, Action.AUTHORIZE}:
            raise TypeError("Invalid action %r" % action)
        if not isinstance(card3ds, bool):
            raise TypeError("Invalid value %r for card3ds. Must be a boolean." % card3ds)
        self.amount = amount  # type:float
        self.currency = currency  # type:str
        self.returnUrl = returnUrl  # type:str
        self.logoImage = logoImage  # type:str
        self.fullPageImage = fullPageImage  # type:str
        self.shopName = shopName  # type:str
        self.shopDescription = shopDescription  # type:str
        self.tagline = tagline  # type:str
        self.css = css  # type:dict[str, str]
        self.termsAndConditionUrl = termsAndConditionUrl  # type:str
        self.privacyPolicyUrl = privacyPolicyUrl  # type:str
        self.imprintUrl = imprintUrl  # type:str
        self.helpUrl = helpUrl  # type:str
        self.contactUrl = contactUrl  # type:str
        self.invoiceId = invoiceId  # type:str
        self.orderId = orderId  # type:str
        self.card3ds = card3ds  # type:bool
        self.additionalAttributes = additionalAttributes  # type:dict[str, str]
        self.excludeTypes = excludeTypes  # type:list[str]
        self.action = action  # type:str
        self.customerId = customerId  # type:str
        self.metadataId = metadataId  # type:str
        self.basketId = basketId  # type:str

    def serialize(self):
        data = {
            "amount": self.amount,
            "currency": self.currency,
            "invoiceId": self.invoiceId,
            "orderId": self.orderId,
            "card3ds": self.card3ds,
            "returnUrl": self.returnUrl,
            "excludeTypes": self.excludeTypes or [],
            "additionalAttributes": self.additionalAttributes,
            "logoImage": self.logoImage or None,
            "fullPageImage": self.fullPageImage or None,
            "shopName": self.shopName,
            "shopDescription": self.shopDescription,
            "tagline": self.tagline,
            "css": self.css,
            "termsAndConditionUrl": self.termsAndConditionUrl,
            "privacyPolicyUrl": self.privacyPolicyUrl,
            "imprintUrl": self.imprintUrl,
            "helpUrl": self.helpUrl,
            "contactUrl": self.contactUrl,
            "resources": {
                "customerId": self.customerId,
                "basketId": self.basketId,
                "metadataId": self.metadataId,
            },
        }
        return data

    @classmethod
    def fromDict(cls, data):
        raise NotImplementedError("Use PaymentPageResponse.fromDict for your responses.")


class PaymentPageResponse(PaymentPage):
    def __init__(
            self,
            payPageId=None,
            paymentId=None,
            redirectUrl=None,
            billingAddressRequired=None,
            shippingAddressRequired=None,
            **kwargs
    ):
        """Create a new PaymentPageResponse.

        To PaymentPage additionally response only params:
        :param payPageId: Id of this payment page
        :type payPageId: str
        :param paymentId: (optional) The ID of the related payment resource. (After success payment)
        :type paymentId: str
        :param redirectUrl: (optional) A unique Hosted Payment Page URL, where the customer completes the payment.
        :type redirectUrl: str
        :param billingAddressRequired: (optional) Determines whether the customer needs to provide a billing address.
        :type billingAddressRequired: bool
        :param shippingAddressRequired: (optional) Determines whether the customer needs to provide a shipping address.
        :type shippingAddressRequired: bool
        """
        super(PaymentPageResponse, self).__init__(**kwargs)
        self.payPageId = payPageId  # type:str
        self.paymentId = paymentId  # type:str
        self.redirectUrl = redirectUrl  # type:str
        self.billingAddressRequired = billingAddressRequired  # type:bool
        self.shippingAddressRequired = shippingAddressRequired  # type:bool

    def serialize(self):
        data = super(PaymentPageResponse, self).serialize()
        data["id"] = self.payPageId
        data["paymentId"] = self.paymentId
        data["redirectUrl"] = self.redirectUrl
        data["billingAddressRequired"] = self.billingAddressRequired
        data["shippingAddressRequired"] = self.shippingAddressRequired
        return data

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        data["payPageId"] = data["id"]
        data["customerId"] = data["resources"].get("customerId")
        data["basketId"] = data["resources"].get("basketId")
        data["metadataId"] = data["resources"].get("metadataId")
        data["paymentId"] = data["resources"].get("paymentId")
        data["card3ds"] = parseBool(data["card3ds"])
        data["shippingAddressRequired"] = parseBool(data["shippingAddressRequired"])
        data["billingAddressRequired"] = parseBool(data["billingAddressRequired"])
        data["action"] = data["action"].lower()  # must be equivalent to enum *Action*
        return cls(**data)
