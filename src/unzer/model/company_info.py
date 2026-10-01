"""The company data of a B2B customer (``companyInfo`` on the customer resource).

Every rule stated here was measured against the sandbox with
``examples/07_probe_b2b_customer.py``. The PHP SDK, the Java SDK, the OpenAPI spec
and docs.unzer.com disagree with each other on most of them, and with the API on
several.
"""
import datetime
import enum
import typing as t

from ..utils import formatBirthDate, parseBirthDate
from .base import BaseModel, JSONValue

if t.TYPE_CHECKING:
    from ..client import UnzerClient


class CompanyRegistrationType(enum.StrEnum):
    """Whether the company is entered in a commercial register.

    The only ``companyInfo`` field whose value the API checks: anything else is
    refused with ``API.410.200.026`` *registrationType value is invalid.* The API
    reads it case-insensitively and stores it in lower case.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/CompanyRegistrationTypes.php
    """

    REGISTERED = "registered"
    NOT_REGISTERED = "not_registered"


class CompanyFunction(enum.StrEnum):
    """The function of the person placing the order within the company.

    ``OWNER`` is the only value any source names. The customer resource does not
    check it -- ``Owner`` and arbitrary text are stored as sent -- but the
    ``paylater-invoice`` authorize refuses anything else for an unregistered
    company (``API.410.100.108``).

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Resources/CustomerFactory.php
    """

    OWNER = "OWNER"


class CompanyType(enum.StrEnum):
    """Legal form of the company.

    The customer resource stores any text, in any case. The ``paylater-invoice``
    authorize requires one of these values, in lower case (``COR.100.301.111``).

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/CompanyTypes.php
    """

    AUTHORITY = "authority"
    ASSOCIATION = "association"
    SOLE = "sole"
    COMPANY = "company"
    OTHER = "other"


class CompanyCommercialSector(enum.StrEnum):
    """Line of business of the company.

    Not checked anywhere measured: the customer resource stores any text, in any
    case -- including the Java SDK's misspelt
    ``WAREHOUSING_AND_SUPPORT_ACTIVITES_FOR_TRANSPORTATION`` -- and the
    ``paylater-invoice`` authorize accepts it. These are the documented values,
    spelt as in the PHP SDK.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/CompanyCommercialSectorItems.php
    """

    OTHER = "OTHER"
    WHOLESALE_TRADE_EXCEPT_VEHICLE_TRADE = "WHOLESALE_TRADE_EXCEPT_VEHICLE_TRADE"
    RETAIL_TRADE_EXCEPT_VEHICLE_TRADE = "RETAIL_TRADE_EXCEPT_VEHICLE_TRADE"
    WATER_TRANSPORT = "WATER_TRANSPORT"
    AIR_TRANSPORT = "AIR_TRANSPORT"
    WAREHOUSING_AND_SUPPORT_ACTIVITIES_FOR_TRANSPORTATION = "WAREHOUSING_AND_SUPPORT_ACTIVITIES_FOR_TRANSPORTATION"
    POSTAL_AND_COURIER_ACTIVITIES = "POSTAL_AND_COURIER_ACTIVITIES"
    ACCOMMODATION = "ACCOMMODATION"
    FOOD_AND_BEVERAGE_SERVICE_ACTIVITIES = "FOOD_AND_BEVERAGE_SERVICE_ACTIVITIES"
    MOTION_PICTURE_PRODUCTION_AND_SIMILAR_ACTIVITIES = "MOTION_PICTURE_PRODUCTION_AND_SIMILAR_ACTIVITIES"
    TELECOMMUNICATIONS = "TELECOMMUNICATIONS"
    COMPUTER_PROGRAMMING_CONSULTANCY_AND_RELATED_ACTIVITIES = "COMPUTER_PROGRAMMING_CONSULTANCY_AND_RELATED_ACTIVITIES"
    INFORMATION_SERVICE_ACTIVITIES = "INFORMATION_SERVICE_ACTIVITIES"
    RENTAL_AND_LEASING_ACTIVITIES = "RENTAL_AND_LEASING_ACTIVITIES"
    TRAVEL_AGENCY_AND_RELATED_ACTIVITIES = "TRAVEL_AGENCY_AND_RELATED_ACTIVITIES"
    SERVICES_TO_BUILDINGS_AND_LANDSCAPE_ACTIVITIES = "SERVICES_TO_BUILDINGS_AND_LANDSCAPE_ACTIVITIES"
    LIBRARIES_AND_SIMILAR_CULTURAL_ACTIVITIES = "LIBRARIES_AND_SIMILAR_CULTURAL_ACTIVITIES"
    SPORTS_ACTIVITIES_AND_AMUSEMENT_AND_RECREATION_ACTIVITIES = (
        "SPORTS_ACTIVITIES_AND_AMUSEMENT_AND_RECREATION_ACTIVITIES")
    OTHER_PERSONAL_SERVICE_ACTIVITIES = "OTHER_PERSONAL_SERVICE_ACTIVITIES"
    NON_RESIDENTIAL_REAL_ESTATE_ACTIVITIES = "NON_RESIDENTIAL_REAL_ESTATE_ACTIVITIES"
    MANAGEMENT_CONSULTANCY_ACTIVITIES = "MANAGEMENT_CONSULTANCY_ACTIVITIES"
    ELECTRICITY_GAS_AND_STEAM_SUPPLY = "ELECTRICITY_GAS_AND_STEAM_SUPPLY"
    WATER_COLLECTION_TREATMENT_AND_SUPPLY = "WATER_COLLECTION_TREATMENT_AND_SUPPLY"
    SEWERAGE = "SEWERAGE"
    MANUFACTURE_OF_FOOD_PRODUCTS = "MANUFACTURE_OF_FOOD_PRODUCTS"
    MANUFACTURE_OF_BEVERAGES = "MANUFACTURE_OF_BEVERAGES"
    MANUFACTURE_OF_TEXTILES = "MANUFACTURE_OF_TEXTILES"
    OTHERS_COMMERCIAL_SECTORS = "OTHERS_COMMERCIAL_SECTORS"
    MANUFACTURE_OF_WEARING_APPAREL = "MANUFACTURE_OF_WEARING_APPAREL"
    MANUFACTURE_OF_LEATHER_AND_RELATED_PRODUCTS = "MANUFACTURE_OF_LEATHER_AND_RELATED_PRODUCTS"
    MANUFACTURE_OF_PHARMACEUTICAL_PRODUCTS = "MANUFACTURE_OF_PHARMACEUTICAL_PRODUCTS"
    REPAIR_AND_INSTALLATION_OF_MACHINERY_AND_EQUIPMENT = "REPAIR_AND_INSTALLATION_OF_MACHINERY_AND_EQUIPMENT"
    TRADE_AND_REPAIR_OF_MOTOR_VEHICLES = "TRADE_AND_REPAIR_OF_MOTOR_VEHICLES"
    PUBLISHING_ACTIVITIES = "PUBLISHING_ACTIVITIES"
    REPAIR_OF_COMPUTERS_AND_GOODS = "REPAIR_OF_COMPUTERS_AND_GOODS"
    PRINTING_AND_REPRODUCTION_OF_RECORDED_MEDIA = "PRINTING_AND_REPRODUCTION_OF_RECORDED_MEDIA"
    MANUFACTURE_OF_FURNITURE = "MANUFACTURE_OF_FURNITURE"
    OTHER_MANUFACTURING = "OTHER_MANUFACTURING"
    ADVERTISING_AND_MARKET_RESEARCH = "ADVERTISING_AND_MARKET_RESEARCH"
    OTHER_PROFESSIONAL_SCIENTIFIC_AND_TECHNICAL_ACTIVITIES = "OTHER_PROFESSIONAL_SCIENTIFIC_AND_TECHNICAL_ACTIVITIES"
    ARTS_ENTERTAINMENT_AND_RECREATION = "ARTS_ENTERTAINMENT_AND_RECREATION"


class CompanyOwner(BaseModel):
    """The owner of a company, embedded in :class:`CompanyInfo` as ``owner``.

    Docs.unzer.com asks for it with sole proprietors. The API requires it in no
    measured case, and stores it for registered and unregistered companies alike.

    Note the casing: the owner's date of birth is ``birthdate``, while the
    customer's is ``birthDate``. The API silently drops an owner ``birthDate``.
    """

    MAX_LENGTHS: t.ClassVar[dict[str, int]] = {
        "firstname": 256,
        "lastname": 256,
    }
    """Measured against the sandbox; see ``examples/06_probe_field_limits.py``."""

    def __init__(
            self,
            firstname: str | None = None,
            lastname: str | None = None,
            birthdate: str | datetime.date | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create a company owner.

        :param firstname: (optional) First name of the owner.
        :param lastname: (optional) Last name of the owner.
        :param birthdate: (optional) Date of birth, as date or in the format
            ``yyyy-mm-dd`` or ``dd.mm.yyyy`` -- the API accepts both and answers
            with the first.
        """
        super().__init__(**kwargs)
        self.firstname = firstname
        self.lastname = lastname
        self.birthdate = birthdate

    @property
    def birthdate(self) -> datetime.datetime | datetime.date | None:
        """Date of birth of the owner."""
        return self._birthdate

    @birthdate.setter
    def birthdate(self, value: str | datetime.date | datetime.datetime | None) -> None:
        # A malformed date is refused by the API with the generic API.410.300.999,
        # which does not name the field. Parsing here names it.
        self._birthdate = parseBirthDate(value)

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "firstname": self.firstname,
            "lastname": self.lastname,
            "birthdate": formatBirthDate(self.birthdate),
        }
        return {key: value for key, value in data.items() if value is not None}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue], client: "UnzerClient | None" = None) -> t.Self:
        """Build an owner from the ``owner`` object of a customer response."""
        return cls(
            firstname=data.get("firstname") or None,
            lastname=data.get("lastname") or None,
            birthdate=data.get("birthdate") or None,
            client=client,
        )


class CompanyInfo(BaseModel):
    """The company data that makes a customer a B2B customer.

    Sent as ``companyInfo`` on the :class:`~unzer.model.customer.Customer`. What
    the API then requires depends on :attr:`registrationType`, measured against the
    sandbox. The rules on customer fields are checked by
    :meth:`Customer.validateBeforeRequest() <unzer.model.customer.Customer.validateBeforeRequest>`,
    the others here:

    ======================== ============================================== =====================
    registrationType         required                                       error code if missing
    ======================== ============================================== =====================
    (always)                 ``registrationType``                           ``API.410.100.120``
    (always)                 ``company`` on the customer                    ``API.410.100.115``
    (always)                 a billing address                              ``API.410.100.128``
    (always)                 its ``street``, ``zip``, ``city``, ``country`` ``API.410.100.107``
    ``registered``           ``commercialRegisterNumber``                   ``API.410.100.110``
    ``not_registered``       ``function``                                   ``API.410.100.119``
    ``not_registered``       ``commercialSector``                           ``API.410.100.116``
    ``not_registered``       ``email`` on the customer                      ``API.410.100.112``
    ``not_registered``, sole ``birthDate`` on the customer                  ``API.410.100.111``
    ======================== ============================================== =====================

    *sole* is a ``companyType`` of ``sole``, in any case.

    The owner's ``birthdate`` does not replace the customer's for a sole
    proprietor. And the address rule has a hole: an empty ``billingAddress: {}`` is
    accepted, while one with only some fields is refused -- this SDK always sends
    every field, so it checks them.

    The customer resource is only the first check. ``paylater-invoice``, the one
    method with B2B, checks more at the authorize (measured):

    * ``companyType`` is required and must be one of :class:`CompanyType`, in lower
      case -- ``COR.100.301.111`` *customer.company.type needs to be provided* or
      *must be a valid type* otherwise. The customer resource accepts it missing.
    * ``function`` must be ``OWNER`` for an unregistered company
      (``API.410.100.108``).
    * The customer needs a first name and an email, registered or not.
    * An owner must carry the customer's name (``API.320.100.135``, which speaks
      of the billing address).
    * ``commercialSector`` is still not checked.

    And an unregistered company drops a ``commercialRegisterNumber`` without an
    error, so the value is lost rather than refused.

    The customer resource stores any text in ``function``, ``commercialSector``
    and ``companyType``, so a customer read back can carry values outside the
    enums. They are typed as strings for that reason; :class:`CompanyFunction`,
    :class:`CompanyCommercialSector` and :class:`CompanyType` hold the documented
    values, and compare equal to them.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Resources/EmbeddedResources/CompanyInfo.php
    """

    MAX_LENGTHS: t.ClassVar[dict[str, int]] = {
        "commercialRegisterNumber": 256,
        "function": 256,
        "commercialSector": 256,
        "companyType": 256,
    }
    """Measured against the sandbox; see ``examples/06_probe_field_limits.py``."""

    def __init__(
            self,
            registrationType: CompanyRegistrationType | str,
            commercialRegisterNumber: str | None = None,
            function: CompanyFunction | str | None = None,
            commercialSector: CompanyCommercialSector | str | None = None,
            companyType: CompanyType | str | None = None,
            owner: CompanyOwner | None = None,
            **kwargs: t.Any,
    ) -> None:
        """Create the company data of a B2B customer.

        :param registrationType: Whether the company is in a commercial register.
        :param commercialRegisterNumber: (optional) Entry in the commercial register.
            Required for a registered company, dropped by the API for an
            unregistered one.
        :param function: (optional) Function of the person ordering, documented is
            only :attr:`CompanyFunction.OWNER`. Required for an unregistered company.
        :param commercialSector: (optional) Line of business, see
            :class:`CompanyCommercialSector`. Required for an unregistered company.
        :param companyType: (optional) Legal form, see :class:`CompanyType`.
        :param owner: (optional) The owner of the company.
        :raises ValueError: For a registration type the API does not know.
        """
        super().__init__(**kwargs)
        self.registrationType = registrationType
        self.commercialRegisterNumber = commercialRegisterNumber
        self.function = function
        self.commercialSector = commercialSector
        self.companyType = companyType
        self.owner = owner

    @property
    def registrationType(self) -> CompanyRegistrationType:
        """Whether the company is in a commercial register."""
        return self._registrationType

    @registrationType.setter
    def registrationType(self, value: CompanyRegistrationType | str) -> None:
        # Strict on purpose: the API refuses an unknown value (API.410.200.026),
        # so a typo is better caught here than there.
        self._registrationType = CompanyRegistrationType(value)

    @classmethod
    def registered(
            cls,
            commercialRegisterNumber: str,
            **kwargs: t.Any,
    ) -> t.Self:
        """Build the company data of a company in a commercial register.

        :param commercialRegisterNumber: Entry in the commercial register.
        :param kwargs: Any further field of :class:`CompanyInfo`.
        """
        return cls(
            registrationType=CompanyRegistrationType.REGISTERED,
            commercialRegisterNumber=commercialRegisterNumber,
            **kwargs,
        )

    @classmethod
    def notRegistered(
            cls,
            commercialSector: CompanyCommercialSector | str = CompanyCommercialSector.OTHER,
            function: CompanyFunction | str = CompanyFunction.OWNER,
            **kwargs: t.Any,
    ) -> t.Self:
        """Build the company data of a company without a register entry.

        The defaults are the ones the PHP SDK's ``CustomerFactory`` uses, and
        cover the two fields the API requires here.

        :param commercialSector: (optional) Line of business, ``OTHER`` by default.
        :param function: (optional) Function of the person ordering, ``OWNER`` by default.
        :param kwargs: Any further field of :class:`CompanyInfo`.
        """
        return cls(
            registrationType=CompanyRegistrationType.NOT_REGISTERED,
            commercialSector=commercialSector,
            function=function,
            **kwargs,
        )

    def validateBeforeRequest(self) -> bool:
        """Check the fields the API requires for the registration type.

        :raises ValueError: If a required field is missing or one is too long.
        """
        super().validateBeforeRequest()
        if self.registrationType is CompanyRegistrationType.REGISTERED:
            required = ("commercialRegisterNumber",)
        else:
            required = ("function", "commercialSector")
        for attr in required:
            if not getattr(self, attr):
                raise ValueError(
                    f"{type(self).__name__} with registrationType "
                    f"{self.registrationType.value!r} misses the attribute *{attr}*."
                )
        if self.owner is not None:
            self.owner.validateBeforeRequest()
        return True

    def serialize(self) -> dict[str, JSONValue]:
        # Missing fields are left out rather than sent as "" or null. Both of those
        # are accepted where the field is optional, but leaving them out is what
        # was measured for every case.
        if self.owner is not None and not isinstance(self.owner, CompanyOwner):
            raise TypeError(f"Expected a CompanyOwner object for owner. Got {type(self.owner)!r}")
        data = {
            "registrationType": self.registrationType.value,
            "commercialRegisterNumber": self.commercialRegisterNumber,
            "function": self.function,
            "commercialSector": self.commercialSector,
            "companyType": self.companyType,
            "owner": self.owner.serialize() if self.owner is not None else None,
        }
        return {key: value for key, value in data.items() if value not in (None, "")}

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue], client: "UnzerClient | None" = None) -> t.Self:
        """Build the company data from the ``companyInfo`` object of a customer response.

        The API answers an unset field with an empty string, and leaves
        ``commercialRegisterNumber`` and ``owner`` out entirely when they are not
        set. Both come back as ``None`` here.
        """
        owner = data.get("owner")
        return cls(
            registrationType=data["registrationType"],
            commercialRegisterNumber=data.get("commercialRegisterNumber") or None,
            function=data.get("function") or None,
            commercialSector=data.get("commercialSector") or None,
            companyType=data.get("companyType") or None,
            owner=CompanyOwner.fromDict(owner, client=client) if owner else None,
            client=client,
        )
