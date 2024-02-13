__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

from .abstract_paymenttype import PaymentType


class Bancontact(PaymentType):
    method = "bancontact"

    REQUIRED_ATTRIBUTES = ["holder"]

    def __init__(
            self,
            holder,
            **kwargs
    ):
        """Create a new Bancontact paymentType ressource.

        :param holder: The holder name.
        :type holder: str
        """
        super(Bancontact, self).__init__(**kwargs)
        self.holder = holder  # type: str

    def serialize(self):
        return {
            "holder": self.holder,
        }

    @classmethod
    def fromDict(cls, data):
        data = data.copy()
        data["key"] = data["id"]
        return cls(**data)
