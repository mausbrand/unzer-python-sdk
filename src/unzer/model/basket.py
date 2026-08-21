import typing as t

from ..utils import parseFloat, roundAmount
from .base import BaseModel, JSONValue
from .basketItem import BasketItem


class Basket(BaseModel):
    """A basket resource.

    Unzer offers this resource in two incompatible schemas. Which one is used depends on
    :attr:`totalValueGross`: as soon as it is set, the basket is sent to the v3 endpoint
    with gross amounts, otherwise the v1 endpoint with :attr:`amountTotalGross` is used.
    The basket items follow the same rule on their own
    (see :class:`unzer.model.BasketItem`), so don't mix the schemas within one basket.

    The Pay later payment methods (e.g. :class:`unzer.model.PaylaterInstallment`)
    require the v3 schema.

    Note that the v2 and v3 endpoints share the same schema, so the newer v3 is used here.
    """

    def __init__(
            self,
            key=None,
            amountTotalGross=None,
            amountTotalVat=None,
            amountTotalDiscount=None,
            totalValueGross=None,
            currencyCode=None,
            orderId=None,
            note=None,
            basketItems=None,
            **kwargs
    ):
        """Create a new Basket.

        :param key: (optional)
        :type key: str
        :param amountTotalGross: (optional) (v1) Total gross amount of the basket
        :type amountTotalGross: float
        :param amountTotalVat: (optional) (v1)
        :type amountTotalVat: float
        :param amountTotalDiscount: (optional) (v1)
        :type amountTotalDiscount: float
        :param totalValueGross: (v3) Total gross amount of the basket.
            Setting it switches this basket to the v3 schema.
        :type totalValueGross: float
        :param currencyCode: (optional) example: EUR
        :type currencyCode: str
        :param orderId: example: s-bsk-XXX
        :type orderId: str
        :param note: (optional)
        :type note: str
        :param basketItems: (optional)
        :type basketItems: list[BasketItem]
        """
        super().__init__(**kwargs)
        if basketItems is None:
            basketItems = []
        self.key = key  # type:str
        self.amountTotalGross = amountTotalGross  # type:float
        self.amountTotalVat = amountTotalVat  # type:float
        self.amountTotalDiscount = amountTotalDiscount  # type:float
        self.totalValueGross = totalValueGross  # type:float
        self.currencyCode = currencyCode  # type:str
        self.orderId = orderId  # type:str
        self.note = note  # type:str
        self.basketItems = basketItems  # type:list[BasketItem]

    def isV3(self) -> bool:
        """Tell whether this basket uses the v3 schema, i.e. :attr:`totalValueGross`."""
        return self.totalValueGross is not None

    @property
    def apiVersion(self) -> str:
        """Provide the API version of the endpoint this basket has to be sent to."""
        return "v3" if self.isV3() else "v1"

    def serialize(self) -> dict[str, JSONValue]:
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
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        """Unserialize a basket of either schema; missing amounts stay ``None``."""
        data = data.copy()
        data["key"] = data["id"]
        data["basketItems"] = [BasketItem.fromDict(basketItem) for basketItem in data.get("basketItems") or []]
        for key in ("amountTotalGross", "amountTotalVat", "amountTotalDiscount", "totalValueGross"):
            data[key] = parseFloat(data.get(key))
        return cls(**data)
