import typing as t
from types import NoneType

from ..utils import parseBool, roundAmount
from .base import BaseModel
from .payment import Action


class PaymentPage(BaseModel):
    """A hosted or embedded payment page.

    Unzer hosts the page, the customer picks a payment method there, and no card
    data reaches your server. The shortest complete flow, and the only one that
    works for every payment method without a frontend integration of your own.

    :attr:`action` decides whether the payment is charged straight away or only
    authorised.

    .. note::
        This is the v1 payment page, which the OpenAPI spec tags as deprecated in
        favour of a v2 on its own host. v1 still works; v2 is not implemented here.
    """

    REQUIRED_ATTRIBUTES: t.ClassVar[list[str]] = [
        "action",
        "amount",
        "currency",
        "returnUrl",
    ]

    def __init__(
            self,
            action: str | Action | None = None,
            amount: float | None = None,
            currency: str = "EUR",
            invoiceId: str | None = None,
            orderId: str | None = None,
            card3ds: bool | None = None,
            returnUrl: str | None = None,
            excludeTypes: list[str] | None = None,
            additionalAttributes: dict[str, str] | None = None,
            logoImage: str | None = None,
            fullPageImage: str | None = None,
            shopName: str | None = None,
            shopDescription: str | None = None,
            tagline: str | None = None,
            css: dict[str, str] | None = None,
            termsAndConditionUrl: str | None = None,
            privacyPolicyUrl: str | None = None,
            imprintUrl: str | None = None,
            helpUrl: str | None = None,
            contactUrl: str | None = None,
            customerId: str | None = None,
            metadataId: str | None = None,
            basketId: str | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new PaymentPage.

        Payment attributes:
        :param action: (required) Action for this paypage: charge or authorize.
            Accepts the enum member or its name in any casing.
        :param amount: (required) The transaction amount.
        :param currency: (required) The transaction currency, in the ISO 4217 alpha-3 format.
        :param invoiceId: (optional) Your internal invoice ID.
        :param orderId: (optional) A unique order ID that identifies the payment on your side.
        :param card3ds: (optional) Switches between 3ds and non 3ds card transactions.
        :param returnUrl: (required) The URL to redirect the customer to after the payment is completed.
        :param excludeTypes: (optional) Exclude some of the payment types from the Payment Page.
        :param additionalAttributes: (optional) Attributes for LinkPay.

        Paypage config:
        :param logoImage: (optional) Your company logo to show in the Embedded Payment Page’s header.
        :param fullPageImage: (optional) The URL of the image to show in the Hosted Payment Page’s background.
        :param shopName: (optional) Your company name to show in the Embedded Payment Page’s header.
        :param shopDescription: (optional) Main description of the purchase.
        :param tagline: (optional) A short description to show in the Payment Page’s header.
        :param css: (optional)
        :param termsAndConditionUrl: (optional) Your Terms and Conditions URL to show in the Payment Page’s footer.
        :param privacyPolicyUrl: (optional) Your Privacy Policy URL to show in the Payment Page’s footer.
        :param imprintUrl: (optional) Your imprint URL to show in the Payment Page’s footer.
        :param helpUrl: (optional) The URL of the help page to show in the Payment Page’s header.
        :param contactUrl: (optional) The URL of the contact page to show in the Payment Page’s header.

        Resources
        :param customerId: (optional) The ID of the customers resource to be used.
        :param metadataId: (optional) The ID of the metadata resource to be used.
        :param basketId: (optional) The ID of the baskets resource to be used.
        """
        super().__init__(**kwargs)
        if excludeTypes is None:
            excludeTypes = []
        if additionalAttributes is None:
            additionalAttributes = {}
        if css is None:
            css = {}
        # The API answers with the upper case name ("CHARGE"), while the request
        # path needs the lower case value ("charge"), so accept both spellings
        # and keep the enum member internally.
        if isinstance(action, str):
            try:
                action = Action(action.lower())
            except ValueError:
                raise TypeError(f"Invalid action {action!r}") from None
        elif not isinstance(action, Action):
            raise TypeError(f"Invalid action {action!r}")
        if not isinstance(card3ds, (bool, NoneType)):
            raise TypeError(
                f"Invalid value {card3ds!r} for card3ds. Must be a boolean or None."
            )
        self.amount: float | None = amount
        self.currency: str = currency
        self.returnUrl: str | None = returnUrl
        self.logoImage: str | None = logoImage
        self.fullPageImage: str | None = fullPageImage
        self.shopName: str | None = shopName
        self.shopDescription: str | None = shopDescription
        self.tagline: str | None = tagline
        self.css: dict[str, str] = css
        self.termsAndConditionUrl: str | None = termsAndConditionUrl
        self.privacyPolicyUrl: str | None = privacyPolicyUrl
        self.imprintUrl: str | None = imprintUrl
        self.helpUrl: str | None = helpUrl
        self.contactUrl: str | None = contactUrl
        self.invoiceId: str | None = invoiceId
        self.orderId: str | None = orderId
        self.card3ds: bool | None = card3ds
        self.additionalAttributes: dict[str, str] = additionalAttributes
        self.excludeTypes: list[str] = excludeTypes
        self.action: Action = action
        self.customerId: str | None = customerId
        self.metadataId: str | None = metadataId
        self.basketId: str | None = basketId

    def serialize(self) -> dict[str, t.Any]:
        return {
            "amount": roundAmount(self.amount),
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

    @classmethod
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
        raise NotImplementedError("Use PaymentPageResponse.fromDict for your responses.")


class PaymentPageResponse(PaymentPage):
    """The payment page as the API returns it.

    Adds the fields only the response has -- most importantly
    :attr:`redirectUrl`, where the customer has to be sent, and
    :attr:`paymentId`, which is how the payment is looked up afterwards.
    """

    def __init__(
            self,
            payPageId: str | None = None,
            paymentId: str | None = None,
            redirectUrl: str | None = None,
            billingAddressRequired: bool | None = None,
            shippingAddressRequired: bool | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new PaymentPageResponse.

        To PaymentPage additionally response only params:
        :param payPageId: Id of this payment page
        :param paymentId: (optional) The ID of the related payment resource. (After success payment)
        :param redirectUrl: (optional) A unique Hosted Payment Page URL, where the customer completes the payment.
        :param billingAddressRequired: (optional) Determines whether the customer needs to provide a billing address.
        :param shippingAddressRequired: (optional) Determines whether the customer needs to provide a shipping address.
        """
        super().__init__(**kwargs)
        self.payPageId: str | None = payPageId
        self.paymentId: str | None = paymentId
        self.redirectUrl: str | None = redirectUrl
        self.billingAddressRequired: bool | None = billingAddressRequired
        self.shippingAddressRequired: bool | None = shippingAddressRequired

    def serialize(self) -> dict[str, t.Any]:
        data = super().serialize()
        data["id"] = self.payPageId
        data["paymentId"] = self.paymentId
        data["redirectUrl"] = self.redirectUrl
        data["billingAddressRequired"] = self.billingAddressRequired
        data["shippingAddressRequired"] = self.shippingAddressRequired
        return data

    @classmethod
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
        data = data.copy()
        data["payPageId"] = data["id"]
        data["customerId"] = data["resources"].get("customerId")
        data["basketId"] = data["resources"].get("basketId")
        data["metadataId"] = data["resources"].get("metadataId")
        data["paymentId"] = data["resources"].get("paymentId")
        data["card3ds"] = parseBool(data["card3ds"])
        data["shippingAddressRequired"] = parseBool(data["shippingAddressRequired"])
        data["billingAddressRequired"] = parseBool(data["billingAddressRequired"])
        # action is converted to the Action enum by __init__
        return cls(**data)
