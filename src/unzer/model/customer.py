import datetime
import typing as t

from .address import Address
from .base import BaseModel, JSONValue
from ..utils import SENTINEL, Sentinel, normalize_language

if t.TYPE_CHECKING:
    from ..client import UnzerClient


class Salutation:
    MR = "mr"
    MRS = "mrs"
    UNKNOWN = "unknown"


class Customer(BaseModel):

    def __init__(
            self,
            firstname,
            lastname,
            salutation=None,
            key=None,
            customerId=None,
            birthDate=None,
            email=None,
            phone=None,
            mobile=None,
            billingAddress=None,
            shippingAddress=None,
            company=None,
            companyData=None,
            language: str | None | Sentinel = SENTINEL,
            **kwargs
    ):
        """Create a new Customer.

        :param key: (optional) (original: id) Customer's generated code by Unzer's Payment
        :type key: str
        :param firstname: Customer's lastname
        :type firstname: str
        :param lastname: Customer's firstname
        :type lastname: str
        :param salutation: (optional) Must be either 'mr', 'mrs' or 'unknown'
        :type salutation: str | Salutation
        :param company: (optional) Company name
        :type company: str
        :param customerId: (optional) Must be unique and identifies the customer.
            Can be used in place of the resource id
        :type customerId: str
        :param birthDate: (optional) Birthdate of the customer in format yyyy-mm-dd or dd.mm.yyyy
        :type birthDate: datetime.datetime | datetime.date | str
        :param email: (optional) Customer's email
        :type email: str
        :param phone: (optional) Customer's phone
        :type phone: str
        :param mobile: (optional) Customer's mobile
        :type mobile: str
        :param billingAddress: (optional) billing address
        :type billingAddress: Address
        :param shippingAddress: (optional) shipping address
        :type shippingAddress: Address
        :param companyData: (optional)
        :type companyData: CompanyInfo
        :param language: (optional) Customer's language as ISO 639-1 code (e.g. ``de``).
            Used by Unzer for customer facing texts and mails.
            An uppercase code (``DE``) is accepted and lowercased, a locale (``de-DE``) is not:
            the API takes the bare lowercase code only (measured against the sandbox,
            everything else fails with HTTP 400 ``API.410.200.057`` *language is invalid.*).
            Left out, the customer takes the language of the client that sends it
            (see :meth:`~unzer.client.UnzerClient.__init__`); pass ``None`` to keep
            the field empty even then and let Unzer pick.
        """
        super().__init__(**kwargs)
        if salutation is None:
            salutation = Salutation.UNKNOWN
        elif salutation not in {Salutation.MR, Salutation.MRS, Salutation.UNKNOWN}:
            raise TypeError("Invalid salutation")
        self.key = key  # type: str
        self.firstname = firstname  # type: str
        self.lastname = lastname  # type: str
        self.salutation = salutation  # type: Salutation
        self.customerId = customerId  # type: str
        self.birthDate = birthDate  # type: datetime.datetime
        self.email = email  # type: str
        self.phone = phone  # type: str
        self.mobile = mobile  # type: str
        self.billingAddress = billingAddress  # type: Address
        self.shippingAddress = shippingAddress  # type: Address
        self.company = company  # type: str
        self.companyData = companyData  # type: CompanyInfo
        if language is SENTINEL:
            # Past the setter, which only takes a language code: the getter turns
            # the sentinel into the language of the client, or None without one.
            self._language = language
        else:
            self.language = language

    @property
    def keyOrCustomerId(self):
        return self.key or self.customerId

    @property
    def salutation(self):
        return self._salutation

    @salutation.setter
    def salutation(self, value):
        if not value:
            value = Salutation.UNKNOWN
        elif value not in {Salutation.MR, Salutation.MRS, Salutation.UNKNOWN}:
            raise TypeError("Invalid salutation %r" % value)
        self._salutation = value

    @property
    def birthDate(self):
        return self._birthDate

    @birthDate.setter
    def birthDate(self, value):
        if not value:
            value = None
        elif isinstance(value, str):
            if "-" in value:  # ISO Date
                value = datetime.datetime.strptime(value, "%Y-%m-%d")
            elif "." in value:  # European Date
                value = datetime.datetime.strptime(value, "%d.%m.%Y")
            else:
                raise TypeError("Invalid date format of %r" % value)
        elif not isinstance(value, (datetime.datetime, datetime.date)):
            raise TypeError("Invalid value %r" % value)
        self._birthDate = value

    @property
    def phone(self):
        return self._phone

    @phone.setter
    def phone(self, value):
        if not value:
            value = None
        self._phone = value

    @property
    def mobile(self):
        return self._mobile

    @mobile.setter
    def mobile(self, value):
        if not value:
            value = None
        self._mobile = value

    @property
    def language(self) -> str | None:
        """The language of this customer, or the one of its client.

        Only a customer that was never given a language falls back to the
        client; ``None`` is an answer of its own and is kept.
        """
        if self._language is not SENTINEL:
            return self._language
        if self._client is None:
            return None
        # The client language is an accept-language value and may name a region
        # ("de-DE"), while the customer resource takes the bare code.
        return normalize_language((self._client.language or "").split("-", 1)[0])

    @language.setter
    def language(self, value: str | None) -> None:
        self._language = normalize_language(value)

    def serialize(self):
        birthDate = self.birthDate
        if isinstance(birthDate, (datetime.datetime, datetime.date)):
            birthDate = birthDate.strftime("%Y-%m-%d")

        billingAddress = self.billingAddress
        if billingAddress is None:
            billingAddress = self.EMPTY_STRING
        else:
            assert isinstance(billingAddress, Address)
            billingAddress = billingAddress.serialize()

        shippingAddress = self.shippingAddress
        if shippingAddress is None:
            shippingAddress = self.EMPTY_STRING
        else:
            assert isinstance(shippingAddress, Address)
            shippingAddress = shippingAddress.serialize()

        return {
            "lastname": self.lastname,
            "firstname": self.firstname,
            "id": self.getString(self.key),
            "salutation": self.getString(self.salutation),
            "company": self.getString(self.company),
            "customerId": self.getString(self.customerId),
            "birthDate": self.getString(birthDate),
            "email": self.getString(self.email),
            "phone": self.getString(self.phone),
            "mobile": self.getString(self.mobile),
            "language": self.getString(self.language),
            "billingAddress": billingAddress,
            "shippingAddress": shippingAddress,

            # Additional information for B2B Customer #ToDo
            # "companyInfo": {
            # 	# Mandatory in case companyInfo is existing, restrict '<' and '>'
            # 	"registrationType": "registered|not_registered",
            # 	# Mandatory for REGISTERED, restrict '<' and '>'
            # 	"commercialRegisterNumber": "...",
            # 	# Mandatory must be the value "OWNER" for NOT_REGISTERED, restrict '<' and '>'
            # 	"function": "...",
            # 	# Mandatory for NOT_REGISTERED, restrict '<' and '>'
            # 	"commercialSector": "..."
            # }
        }

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue], client: "UnzerClient | None" = None) -> t.Self:
        """Build a customer from an API response.

        :param data: The customer resource as the API sent it.
        :param client: (optional) The client that fetched it, attached to the
            new customer -- see :meth:`~unzer.model.base.BaseModel.bind_client`.
        """
        data = data.copy()
        data["key"] = data["id"]
        data["billingAddress"] = Address.fromDict(data["billingAddress"])
        data["shippingAddress"] = Address.fromDict(data["shippingAddress"])
        return cls(**data, client=client)
