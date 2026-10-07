import typing as t

from ..utils import parseFloat, roundAmount
from .base import BaseModel
from .basketItem import BasketItem


class Basket(BaseModel):
    """A basket resource.

    Unzer offers this resource in two incompatible schemas. Which one is used depends on
    :attr:`totalValueGross`: as soon as it is set, the basket is sent to the v3 endpoint
    with gross amounts, otherwise the v1 endpoint with :attr:`amountTotalGross` is used.
    The basket items follow the same rule on their own
    (see :class:`unzer.model.BasketItem`), so don't mix the schemas within one basket.
    Measured: a v3 item in a v1 basket is accepted with a 201 and every item amount
    stored as ``0.0000``, silently, while a v1 item in a v3 basket is refused with
    ``API.600.410.051``. A basket is also only readable through the schema it was
    created with, ``API.600.410.024`` otherwise.

    Both schemas are accepted by every payment method measured so far -- a sandbox
    authorize with Klarna and with :class:`unzer.model.PaylaterInstallment` succeeds
    on either. The documentation claims the Pay later methods require v3; the API does
    not enforce it. What does differ is validation: v3 reconciles
    :attr:`totalValueGross` against the items to the cent (``API.600.410.062``),
    v1 checks nothing at all.

    Note that the v2 and v3 endpoints share the same schema, so the newer v3 is used here.
    """

    def __init__(
            self,
            key: str | None = None,
            amountTotalGross: float | None = None,
            amountTotalVat: float | None = None,
            amountTotalDiscount: float | None = None,
            totalValueGross: float | None = None,
            currencyCode: str | None = None,
            orderId: str | None = None,
            note: str | None = None,
            basketItems: list[BasketItem] | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new Basket.

        :param key: (optional)
        :param amountTotalGross: (optional) (v1) Total gross amount of the basket
        :param amountTotalVat: (optional) (v1)
        :param amountTotalDiscount: (optional) (v1)
        :param totalValueGross: (v3) Total gross amount of the basket.
            Setting it switches this basket to the v3 schema.
        :param currencyCode: (optional) example: EUR
        :param orderId: example: s-bsk-XXX
        :param note: (optional)
        :param basketItems: (optional)
        """
        super().__init__(**kwargs)
        if basketItems is None:
            basketItems = []
        self.key: str | None = key
        self.amountTotalGross: float | None = amountTotalGross
        self.amountTotalVat: float | None = amountTotalVat
        self.amountTotalDiscount: float | None = amountTotalDiscount
        self.totalValueGross: float | None = totalValueGross
        self.currencyCode: str | None = currencyCode
        self.orderId: str | None = orderId
        self.note: str | None = note
        self.basketItems: list[BasketItem] = basketItems

    def isV3(self) -> bool:
        """Tell whether this basket uses the v3 schema, i.e. :attr:`totalValueGross`."""
        return self.totalValueGross is not None

    @property
    def apiVersion(self) -> str:
        """Provide the API version of the endpoint this basket has to be sent to."""
        return "v3" if self.isV3() else "v1"

    def serialize(self) -> dict[str, t.Any]:
        """Serialize this basket in the schema implied by :meth:`isV3`."""
        data = {
            "id": self.key,
            "currencyCode": self.getString(self.currencyCode),
            "orderId": self.getString(self.orderId),
            # note is missing from the v3 schema of the API reference, but both the
            # documented v3 example and the PHP SDK's v2 model do have it
            "note": self.getString(self.note),
            "basketItems": [bi.serialize() for bi in self.basketItems],
        }
        if self.isV3():
            data["totalValueGross"] = roundAmount(self.totalValueGross)
        else:
            data |= {
                "amountTotalGross": roundAmount(self.amountTotalGross),
                "amountTotalVat": roundAmount(self.amountTotalVat),
                "amountTotalDiscount": roundAmount(self.amountTotalDiscount),
            }
        return data

    @classmethod
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
        """Unserialize a basket of either schema; missing amounts stay ``None``."""
        data = data.copy()
        data["key"] = data["id"]
        data["basketItems"] = [BasketItem.fromDict(basketItem) for basketItem in data.get("basketItems") or []]
        for key in ("amountTotalGross", "amountTotalVat", "amountTotalDiscount", "totalValueGross"):
            data[key] = parseFloat(data.get(key))
        return cls(**data)
