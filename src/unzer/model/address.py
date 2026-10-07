import typing as t

from .base import BaseModel


class Address(BaseModel):
    """A billing or shipping address.

    The wire format has a single ``name`` field, which this model splits into
    :attr:`firstname` and :attr:`lastname` and joins again on serialisation. Note
    that it calls the postcode ``zip``, while the attribute is :attr:`zipCode`.

    The API is inconsistent about the name and the SDK mirrors it rather than hiding
    it: an address carries one joined ``name``, while the
    :class:`~unzer.model.customer.Customer` that holds the address sends ``firstname``
    and ``lastname`` as two fields. They are limited accordingly -- 81 characters for
    the joined name here, 40 per field there -- so the same person can pass one check
    and fail the other.
    """

    MAX_LENGTHS: t.ClassVar[dict[str, int]] = {
        # The limit is on the joined `name`, not on either half: measured from both
        # directions, a long first name with a short last one and the reverse both
        # fail at 82. Checking the two parts separately would let an unbalanced pair
        # through. The joining space counts.
        "name": 81,
        "street": 64,
        "zipCode": 10,
        "city": 30,
    }
    """Measured against the sandbox; see ``examples/06_probe_field_limits.py``.

    ``state`` and ``country`` are left out on purpose. Both are format-bound (ISO
    3166-2 and ISO A2), so an over-long value there is a malformed code rather than
    a length problem, and the API says so with a different error.
    """

    def __init__(
            self,
            firstname: str,
            lastname: str | None,
            street: str | None = None,
            state: str | None = None,
            zipCode: str | None = None,
            city: str | None = None,
            country: str | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a new Address.

        :param firstname: Address first name. Together with the last name at most
            81 characters, because the wire format joins them into one ``name``.
        :param lastname: Address last name, see above.
        :param street: (optional) Address street (max. 64 chars). Required in case of billing address.
        :param state: (optional) Address state in ISO 3166-2 format (max. 8 chars). Required in case of billing address.
        :param zipCode: (optional) Address zip code (max. 10 chars). Required in case of billing address.
        :param city: (optional) Address city (max. 30 chars). Required in case of billing address.
        :param country: (optional) Address country in ISO A2 format (max. 2 chars). Required in case of billing address.
        """
        super().__init__(**kwargs)
        self.firstname: str = firstname
        self.lastname: str | None = lastname
        self.street: str | None = street
        self.state: str | None = state
        self.zipCode: str | None = zipCode
        self.city: str | None = city
        self.country: str | None = country

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

    def serialize(self) -> dict[str, t.Any]:
        return {
            "name": self.getString(self.name),
            "street": self.getString(self.street),
            "state": self.getString(self.state),
            "zip": self.getString(self.zipCode),
            "city": self.getString(self.city),
            "country": self.getString(self.country),
        }

    @classmethod
    def fromDict(cls, data: dict[str, t.Any]) -> t.Self:
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
