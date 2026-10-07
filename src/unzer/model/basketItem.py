import typing as t

from ..utils import parseFloat
from .base import BaseModel


class BasketItem(BaseModel):
    """A single line item of a :class:`~unzer.model.Basket`.

    Follows the same two schemas as the basket around it, and on its own: the
    field set decides which one, so do not mix them within one basket. See
    :class:`~unzer.model.Basket`.
    """

    def __init__(
            self,
            basketItemReferenceId: str | None = None,
            unit: str | None = None,
            quantity: int | None = None,
            amountDiscount: float | None = None,
            vat: float | None = None,
            amountGross: float | None = None,
            amountVat: float | None = None,
            amountPerUnit: float | None = None,
            amountNet: float | None = None,
            amountPerUnitGross: float | None = None,
            amountDiscountPerUnitGross: float | None = None,
            title: str | None = None,
            subTitle: str | None = None,
            imageUrl: str | None = None,
            participantId: str | None = None,
            kind: str | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new BasketItem.

        The amount attributes come in two flavours, see :class:`unzer.model.Basket`:
        :attr:`amountPerUnitGross` and :attr:`amountDiscountPerUnitGross` belong to the
        v3 schema, the remaining ``amount*`` attributes to the v1 schema.

        :param basketItemReferenceId: (optional) Unique basket item reference ID (within the basket)
        :param unit: (optional) Unit description of the item e.g. &quot;pc&quot;
        :param quantity: Integer Quantity of the basket item format: int32
        :param amountDiscount: (optional) (v1) Discount amount for the basket item
            (multiplied by the :attr:`quantity`) format: float
        :param vat: (optional in v1, mandatory in v3 -- ``API.600.410.052``) Integer
            Vat value for the basket item in percent (0-100) format: int32
        :param amountGross: (optional) (v1) Gross amount (= amountNet + amountVat) in the specified currency.
            Equals amountNet if vat value is 0 format: float
        :param amountVat: (optional) (v1) Vat amount. Equals 0 if vat value is 0.
            Should equal the :attr:`vat` multiplied by :attr:`amountNet` for each basket item. format: float
        :param amountPerUnit: (v1) NET amount per unit format: float
        :param amountNet: (optional) (v1) Net amount. Equals amountGross if vat value is 0. format: float
        :param amountPerUnitGross: (v3) GROSS amount per unit.
            Setting it switches this item to the v3 schema. format: float
        :param amountDiscountPerUnitGross: (optional) (v3) GROSS discount amount per unit format: float
        :param title: Title of the basket item (max. 255)
        :param subTitle: (optional) The defined subTitle which is displayed on our Payment Page later on
        :param imageUrl: (optional) The defined imageUrl for the related basketItem
            and will be displayed on our Payment Page
        :param participantId: (optional) (v1) Only valid for marketplace payment:
            Channel Id(s) of marketplace's participant(s).
        :param kind: (original: type) (optional)
        """
        super().__init__(**kwargs)
        self.basketItemReferenceId: str | None = basketItemReferenceId
        self.unit: str | None = unit
        self.quantity: int | None = quantity
        self.amountDiscount: float | None = amountDiscount
        self.vat: float | None = vat
        self.amountGross: float | None = amountGross
        self.amountVat: float | None = amountVat
        self.amountPerUnit: float | None = amountPerUnit
        self.amountNet: float | None = amountNet
        self.amountPerUnitGross: float | None = amountPerUnitGross
        self.amountDiscountPerUnitGross: float | None = amountDiscountPerUnitGross
        self.title: str | None = title
        self.subTitle: str | None = subTitle
        self.imageUrl: str | None = imageUrl
        self.participantId: str | None = participantId
        self.kind: str | None = kind

    def isV3(self) -> bool:
        """Tell whether this item uses the v3 schema, i.e. gross amounts per unit."""
        return self.amountPerUnitGross is not None or self.amountDiscountPerUnitGross is not None

    def serialize(self) -> dict[str, t.Any]:
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
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
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
