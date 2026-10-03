"""The company data of a B2B customer (``companyInfo`` on the customer resource).

The behaviour described in this module was observed on sandbox accounts with
``examples/07_probe_b2b_customer.py``. It describes those accounts, not a contract:
production, another keypair or another partner setup may behave differently, and
Unzer can change it at any time. The SDK enforces none of it -- the API answers a
violation itself. The PHP SDK, the Java SDK, the OpenAPI spec and docs.unzer.com
disagree with each other on most points, and with the sandbox on several.
"""
import datetime
import enum
import typing as t

from ..utils import format_birth_date, parse_birth_date
from .base import BaseModel, JSONValue

if t.TYPE_CHECKING:
    from ..client import UnzerClient


class CompanyRegistrationType(enum.StrEnum):
    """Whether the company is entered in a commercial register.

    In the sandbox, the only ``companyInfo`` field whose value was checked: anything
    else was refused with ``API.410.200.026`` *registrationType value is invalid.*,
    and the value was read case-insensitively and stored in lower case.

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/CompanyRegistrationTypes.php
    """

    REGISTERED = "registered"
    NOT_REGISTERED = "not_registered"


class CompanyFunction(enum.StrEnum):
    """The function of the person placing the order within the company.

    ``OWNER`` is the only value any source names. In the sandbox the customer
    resource stored ``Owner`` and arbitrary text as sent, while the
    ``paylater-invoice`` authorize refused anything else for an unregistered company
    (``API.410.100.108``).

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Resources/CustomerFactory.php
    """

    OWNER = "OWNER"


class CompanyType(enum.StrEnum):
    """Legal form of the company.

    In the sandbox the customer resource stored any text, in any case, while the
    ``paylater-invoice`` authorize asked for one of these values, in lower case
    (``COR.100.301.111``).

    .. seealso:: https://github.com/unzerdev/php-sdk/blob/main/src/Constants/CompanyTypes.php
    """

    AUTHORITY = "authority"
    ASSOCIATION = "association"
    SOLE = "sole"
    COMPANY = "company"
    OTHER = "other"


class CompanyCommercialSector(enum.StrEnum):
    """Line of business of the company.

    Not checked anywhere in the sandbox: the customer resource stored any text, in
    any case -- including the Java SDK's misspelt
    ``WAREHOUSING_AND_SUPPORT_ACTIVITES_FOR_TRANSPORTATION`` -- and the
    ``paylater-invoice`` authorize accepted it. These are the documented values,
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

    Docs.unzer.com asks for it with sole proprietors. In the sandbox it was required
    in no case tried, and stored for registered and unregistered companies alike.

    Note the casing: the owner's date of birth is ``birthdate``, while the
    customer's is ``birthDate``. In the sandbox an owner ``birthDate`` was dropped
    without an error.
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
            ``yyyy-mm-dd`` or ``dd.mm.yyyy``; it is sent as the first.
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
        # The sandbox refused a malformed date with the generic API.410.300.999,
        # which does not name the field. Parsing here names it.
        self._birthdate = parse_birth_date(value)

    def serialize(self) -> dict[str, JSONValue]:
        data = {
            "firstname": self.firstname,
            "lastname": self.lastname,
            "birthdate": format_birth_date(self.birthdate),
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

    Sent as ``companyInfo`` on the :class:`~unzer.model.customer.Customer`. What a
    payment then needs depends on :attr:`registrationType`. The table is what the
    whole ``paylater-invoice`` flow asked for on one sandbox keypair -- an
    observation, not a contract (see the module docstring); other methods were not
    tried. This SDK does **not** check it; a violation comes back as
    :class:`~unzer.model.error.ErrorResponse`. Codes starting with ``API.410`` came
    already when the customer was created, ``COR`` and ``API.320`` only at the
    authorize -- worth knowing when debugging, irrelevant otherwise:

    ======================== ============================================== ==============================
    registrationType         needed for a ``paylater-invoice`` payment      refused with
    ======================== ============================================== ==============================
    (always)                 ``registrationType``                           ``API.410.100.120``
    (always)                 ``company`` on the customer                    ``API.410.100.115``
    (always)                 a billing address                              ``API.410.100.128``
    (always)                 its ``street``, ``zip``, ``city``, ``country`` ``API.410.100.107``
    (always)                 ``firstname`` and ``email`` on the customer    ``COR.100.301.111``
    (always)                 ``companyType``, one of :class:`CompanyType`   ``COR.100.301.111``
    ``registered``           ``commercialRegisterNumber``                   ``API.410.100.110``
    ``not_registered``       ``function``, and it must be ``OWNER``         ``API.410.100.119`` / ``.108``
    ``not_registered``       ``commercialSector``                           ``API.410.100.116``
    ``not_registered``       ``email`` on the customer                      ``API.410.100.112``
    ``not_registered``, sole ``birthDate`` on the customer                  ``API.410.100.111``
    with an owner            the owner carries the customer's name          ``API.320.100.135``
    ======================== ============================================== ==============================

    *sole* is a ``companyType`` of ``sole``, in any case. ``companyType`` had to be
    lower case; several of Unzer's own shop plugins send the placeholder
    ``"Company Type"``, which suggests other setups do not insist -- not verified.
    The customer's last name was not tried on its own. The owner's ``birthdate`` did
    not replace the customer's for a sole proprietor, ``commercialSector`` was not
    checked, and the salutation was not needed (it defaults to ``unknown``).

    An unregistered company had a ``commercialRegisterNumber`` dropped without an
    error, so the value is lost rather than refused.

    The sandbox's customer resource stored any text in ``function``,
    ``commercialSector`` and ``companyType``, so a customer read back can carry
    values outside the enums. They are typed as strings for that reason; :class:`CompanyFunction`,
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
            Asked for with a registered company, dropped with an unregistered one
            (sandbox).
        :param function: (optional) Function of the person ordering, documented is
            only :attr:`CompanyFunction.OWNER`. Asked for with an unregistered
            company (sandbox).
        :param commercialSector: (optional) Line of business, see
            :class:`CompanyCommercialSector`. Asked for with an unregistered company
            (sandbox).
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
        # Strict like every enum here. The sandbox refused an unknown value too
        # (API.410.200.026).
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
    def not_registered(
            cls,
            commercialSector: CompanyCommercialSector | str = CompanyCommercialSector.OTHER,
            function: CompanyFunction | str = CompanyFunction.OWNER,
            **kwargs: t.Any,
    ) -> t.Self:
        """Build the company data of a company without a register entry.

        The defaults are the ones the PHP SDK's ``CustomerFactory`` uses, and
        cover the two fields the sandbox asked for here.

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
        """Check the field lengths, of the owner too.

        :raises ValueError: If a field is too long.
        """
        super().validateBeforeRequest()
        if self.owner is not None:
            self.owner.validateBeforeRequest()
        return True

    def serialize(self) -> dict[str, JSONValue]:
        # Missing fields are left out rather than sent as "" or null. The sandbox
        # accepted both where the field was optional, but leaving them out is what
        # was tried for every case.
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

        An unset field may come as an empty string or be missing altogether -- the
        sandbox did both. Either becomes ``None`` here.
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
