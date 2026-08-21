import datetime

from .address import Address
from .base import BaseModel


class Salutation:
    """Salutation of a customer.

    ``unknown`` is a real value here, not a placeholder: it is what the API answers
    for a customer whose salutation is not known.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/Salutations.php
    """

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
            raise TypeError(f"Invalid salutation {value!r}")
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
                raise TypeError(f"Invalid date format of {value!r}")
        elif not isinstance(value, (datetime.datetime, datetime.date)):
            raise TypeError(f"Invalid value {value!r}")
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

    def serialize(self):
        birthDate = self.birthDate
        if isinstance(birthDate, (datetime.datetime, datetime.date)):
            birthDate = birthDate.strftime("%Y-%m-%d")

        # An empty string is rejected by the API with API.410.300.007
        # ("HTTP message not readable") because the field is an object, not a
        # string. null is accepted, so missing addresses are sent as None.
        addresses = {}
        for name in ("billingAddress", "shippingAddress"):
            address = getattr(self, name)
            if address is None:
                addresses[name] = None
            elif isinstance(address, Address):
                addresses[name] = address.serialize()
            else:
                raise TypeError(
                    f"Expected an Address object for {name}. Got {type(address)!r}"
                )
        billingAddress = addresses["billingAddress"]
        shippingAddress = addresses["shippingAddress"]

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
    def fromDict(cls, data):
        data = data.copy()
        data["key"] = data["id"]
        data["billingAddress"] = Address.fromDict(data["billingAddress"])
        data["shippingAddress"] = Address.fromDict(data["shippingAddress"])
        return cls(**data)
