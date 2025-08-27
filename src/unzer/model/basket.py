from .base import BaseModel
from .basketItem import BasketItem


class Basket(BaseModel):
    def __init__(
            self,
            key=None,
            amountTotalGross=None,
            amountTotalVat=None,
            amountTotalDiscount=None,
            currencyCode=None,
            orderId=None,
            note=None,
            basketItems=None,
            **kwargs
    ):
        """Create a new Basket.

        :param key: (optional)
        :type key: str
        :param amountTotalGross: (optional)
        :type amountTotalGross: float
        :param amountTotalVat: (optional)
        :type amountTotalVat: float
        :param amountTotalDiscount: (optional)
        :type amountTotalDiscount: float
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
        self.currencyCode = currencyCode  # type:str
        self.orderId = orderId  # type:str
        self.note = note  # type:str
        self.basketItems = basketItems  # type:list[BasketItem]

    def serialize(self):
        return {
            "id": self.key,
            "amountTotalGross": self.amountTotalGross,
            "amountTotalVat": self.amountTotalVat,
            "amountTotalDiscount": self.amountTotalDiscount,
            "currencyCode": self.getString(self.currencyCode),
            "orderId": self.getString(self.orderId),
            "note": self.getString(self.note),
            "basketItems": [bi.serialize() for bi in self.basketItems],
        }

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        data["key"] = data["id"]
        data["basketItems"] = [BasketItem.fromDict(basketItem) for basketItem in data["basketItems"]]
        data["amountTotalGross"] = float(data["amountTotalGross"])
        data["amountTotalVat"] = float(data["amountTotalVat"])
        data["amountTotalDiscount"] = float(data["amountTotalDiscount"])
        return cls(**data)
