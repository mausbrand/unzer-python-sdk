import typing as t

from ..utils import parseFloat
from .base import BaseModel, JSONValue


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
            amountPerUnitGross=None,
            amountDiscountPerUnitGross=None,
            title=None,
            subTitle=None,
            imageUrl=None,
            participantId=None,
            kind=None,
            **kwargs
    ):
        """Create a new BasketItem.

        The amount attributes come in two flavours, see :class:`unzer.model.Basket`:
        :attr:`amountPerUnitGross` and :attr:`amountDiscountPerUnitGross` belong to the
        v3 schema, the remaining ``amount*`` attributes to the v1 schema.

        :param basketItemReferenceId: (optional) Unique basket item reference ID (within the basket)
        :type basketItemReferenceId: str
        :param unit: (optional) Unit description of the item e.g. &quot;pc&quot;
        :type unit: str
        :param quantity: Integer Quantity of the basket item format: int32
        :type quantity: int
        :param amountDiscount: (optional) (v1) Discount amount for the basket item
            (multiplied by the :attr:`quantity`) format: float
        :type amountDiscount: float
        :param vat: (optional) Integer Vat value for the basket item in percent (0-100) format: int32
        :type vat: int
        :param amountGross: (optional) (v1) Gross amount (= amountNet + amountVat) in the specified currency.
            Equals amountNet if vat value is 0 format: float
        :type amountGross: float
        :param amountVat: (optional) (v1) Vat amount. Equals 0 if vat value is 0.
            Should equal the :attr:`vat` multiplied by :attr:`amountNet` for each basket item. format: float
        :type amountVat: float
        :param amountPerUnit: (v1) NET amount per unit format: float
        :type amountPerUnit: float
        :param amountNet: (optional) (v1) Net amount. Equals amountGross if vat value is 0. format: float
        :type amountNet: str
        :param amountPerUnitGross: (v3) GROSS amount per unit.
            Setting it switches this item to the v3 schema. format: float
        :type amountPerUnitGross: float
        :param amountDiscountPerUnitGross: (optional) (v3) GROSS discount amount per unit format: float
        :type amountDiscountPerUnitGross: float
        :param title: Title of the basket item (max. 255)
        :type title: str
        :param subTitle: (optional) The defined subTitle which is displayed on our Payment Page later on
        :type subTitle: str
        :param imageUrl: (optional) The defined imageUrl for the related basketItem
            and will be displayed on our Payment Page
        :type imageUrl: str
        :param participantId: (optional) (v1) Only valid for marketplace payment:
            Channel Id(s) of marketplace's participant(s).
        :type participantId: str
        :param kind: (original: type) (optional)
        :type kind: str
        """
        super().__init__(**kwargs)
        self.basketItemReferenceId = basketItemReferenceId
        self.unit = unit
        self.quantity = quantity
        self.amountDiscount = amountDiscount
        self.vat = vat
        self.amountGross = amountGross
        self.amountVat = amountVat
        self.amountPerUnit = amountPerUnit
        self.amountNet = amountNet
        self.amountPerUnitGross = amountPerUnitGross
        self.amountDiscountPerUnitGross = amountDiscountPerUnitGross
        self.title = title
        self.subTitle = subTitle
        self.imageUrl = imageUrl
        self.participantId = participantId
        self.kind = kind

    def isV3(self) -> bool:
        """Tell whether this item uses the v3 schema, i.e. gross amounts per unit."""
        return self.amountPerUnitGross is not None or self.amountDiscountPerUnitGross is not None

    def serialize(self) -> dict[str, JSONValue]:
        """Serialize this item in the schema implied by :meth:`isV3`."""
        data = {
            "basketItemReferenceId": self.getString(self.basketItemReferenceId),
            "unit": self.getString(self.unit),
            "quantity": self.quantity,
            "vat": self.vat,
            "title": self.getString(self.title),
            "subTitle": self.getString(self.subTitle),
            "imageUrl": self.getString(self.imageUrl),
            "type": self.getString(self.kind),
        }
        if self.isV3():
            data |= {
                "amountPerUnitGross": self.amountPerUnitGross,
                "amountDiscountPerUnitGross": self.amountDiscountPerUnitGross,
            }
        else:
            data |= {
                "amountDiscount": self.amountDiscount,
                "amountGross": self.amountGross,
                "amountVat": self.amountVat,
                "amountPerUnit": self.amountPerUnit,
                "amountNet": self.amountNet,
                # The v3 schema knows no participantId
                "participantId": self.getString(self.participantId),
            }
        return data

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        """Unserialize an item of either schema; missing amounts stay ``None``."""
        data = data.copy()
        data["kind"] = data.get("type")
        for key in (
                "amountGross",
                "amountVat",
                "amountPerUnit",
                "amountNet",
                "amountDiscount",
                "amountPerUnitGross",
                "amountDiscountPerUnitGross",
                "vat",
        ):
            data[key] = parseFloat(data.get(key))
        if data.get("quantity") is not None:
            data["quantity"] = int(data["quantity"])
        return cls(**data)
