from .base import BaseModel


class Address(BaseModel):
    """A billing or shipping address.

    The wire format has a single ``name`` field, which this model splits into
    :attr:`firstname` and :attr:`lastname` and joins again on serialisation. Note
    that it calls the postcode ``zip``, while the attribute is :attr:`zipCode`.
    """

    def __init__(
            self,
            firstname,
            lastname,
            street=None,
            state=None,
            zipCode=None,
            city=None,
            country=None,
            **kwargs
    ):
        """Create a new Address.

        :param firstname: Address first name. Together with the last name at most
            81 characters, because the wire format joins them into one ``name``.
        :type firstname: str
        :param lastname: Address last name, see above.
        :type lastname: str
        :param street: (optional) Address street (max. 50 chars). Required in case of billing address.
        :type street: str
        :param state: (optional) Address state in ISO 3166-2 format (max. 8 chars). Required in case of billing address.
        :type state: str
        :param zipCode: (optional) Address zip code (max. 10 chars). Required in case of billing address.
        :type zipCode: str
        :param city: (optional) Address city (max. 30 chars). Required in case of billing address.
        :type city: str
        :param country: (optional) Address country in ISO A2 format (max. 2 chars). Required in case of billing address.
        :type country: str
        """
        super().__init__(**kwargs)
        self.firstname = firstname  # type: str
        self.lastname = lastname  # type: str
        self.street = street  # type: str
        self.state = state  # type: str
        self.zipCode = zipCode  # type: str
        self.city = city  # type: str
        self.country = country  # type: str

    @property
    def name(self) -> str:
        """First and last name joined, which is how the API expects an address."""
        return f"{self.getString(self.firstname)} {self.getString(self.lastname)}"

    @name.setter
    def name(self, name: str) -> None:
        """Split a name on the first space; everything after it is the last name.

        A name without a space becomes the first name and leaves the last name
        unset, which is the best that can be done without guessing.
        """
        try:
            self.firstname, self.lastname = name.split(" ", 1)
        except ValueError:
            self.firstname, self.lastname = name, None

    def serialize(self):
        return {
            "name": self.getString(self.name),
            "street": self.getString(self.street),
            "state": self.getString(self.state),
            "zip": self.getString(self.zipCode),
            "city": self.getString(self.city),
            "country": self.getString(self.country),
        }

    @classmethod
    def fromDict(cls, data):
        try:
            firstname, lastname = data["name"].split(" ", 1)
        except ValueError:
            firstname, lastname = data["name"], None
        return cls(
            firstname=firstname,
            lastname=lastname,
            street=data["street"],
            state=data["state"],
            zipCode=data["zip"],
            city=data["city"],
            country=data["country"],
        )
