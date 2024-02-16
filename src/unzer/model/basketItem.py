from .base import BaseModel


class BasketItem(BaseModel):
    def __init__(
            self,
            basketItemReferenceId=None,
            unit=None,
            quantity=None,
            amountDiscount=None,
            vat=None,
            amountGross=None,
            amountVat=None,
            amountPerUnit=None,
            amountNet=None,
            title=None,
            subTitle=None,
            imageUrl=None,
            participantId=None,
            kind=None,
            **kwargs
    ):
        """Create a new BasketItem.

        :param basketItemReferenceId: (optional) Unique basket item reference ID (within the basket)
        :type basketItemReferenceId: str
        :param unit: (optional) Unit description of the item e.g. &quot;pc&quot;
        :type unit: str
        :param quantity: Integer Quantity of the basket item format: int32
        :type quantity: int
        :param amountDiscount: (optional) Discount amount for the basket item
            (multiplied by the :attr:`quantity`) format: float
        :type amountDiscount: float
        :param vat: (optional) Integer Vat value for the basket item in percent (0-100) format: int32
        :type vat: int
        :param amountGross: (optional) Gross amount (= amountNet + amountVat) in the specified currency.
            Equals amountNet if vat value is 0 format: float
        :type amountGross: float
        :param amountVat: (optional) Vat amount. Equals 0 if vat value is 0.
            Should equal the :attr:`vat` multiplied by :attr:`amountNet` for each basket item. format: float
        :type amountVat: float
        :param amountPerUnit: NET amount per unit format: float
        :type amountPerUnit: float
        :param amountNet: (optional) Net amount. Equals amountGross if vat value is 0. format: float
        :type amountNet: str
        :param title: Title of the basket item (max. 255)
        :type title: str
        :param subTitle: (optional) The defined subTitle which is displayed on our Payment Page later on
        :type subTitle: str
        :param imageUrl: (optional) The defined imageUrl for the related basketItem
            and will be displayed on our Payment Page
        :type imageUrl: str
        :param participantId: (optional) Only valid for marketplace payment:
            Channel Id(s) of marketplace's participant(s).
        :type participantId: str
        :param kind: (original: type) (optional)
        :type kind: str
        """
        self.basketItemReferenceId = basketItemReferenceId
        self.unit = unit
        self.quantity = quantity
        self.amountDiscount = amountDiscount
        self.vat = vat
        self.amountGross = amountGross
        self.amountVat = amountVat
        self.amountPerUnit = amountPerUnit
        self.amountNet = amountNet
        self.title = title
        self.subTitle = subTitle
        self.imageUrl = imageUrl
        self.participantId = participantId
        self.kind = kind

    def serialize(self):
        return {
            "basketItemReferenceId": self.getString(self.basketItemReferenceId),
            "unit": self.getString(self.unit),
            "quantity": self.quantity,
            "amountDiscount": self.amountDiscount,
            "vat": self.vat,
            "amountGross": self.amountGross,
            "amountVat": self.amountVat,
            "amountPerUnit": self.amountPerUnit,
            "amountNet": self.amountNet,
            "title": self.getString(self.title),
            "subTitle": self.getString(self.subTitle),
            "imageUrl": self.getString(self.imageUrl),
            "participantId": self.getString(self.participantId),
            "type": self.getString(self.kind),
        }

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        data["kind"] = data["type"]
        data["amountGross"] = float(data["amountGross"])
        data["amountVat"] = float(data["amountVat"])
        data["amountPerUnit"] = float(data["amountPerUnit"])
        data["amountNet"] = float(data["amountNet"])
        data["quantity"] = int(data["quantity"])
        data["vat"] = float(data["vat"])
        return cls(**data)
