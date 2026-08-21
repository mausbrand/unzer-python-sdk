import datetime
import typing as t

from ..utils import parseBool, parseDate, parseFloat, parseTimestamp
from .base import BaseModel, JSONValue


class InstallmentRate(BaseModel):
    """A single rate (monthly payment) of an :class:`InstallmentPlan`."""

    def __init__(
            self,
            date: datetime.date | None = None,
            rate: float | None = None,
            **kwargs,
    ):
        """Create a new InstallmentRate.

        :param date: Due date of this rate.
        :param rate: Amount payable at :attr:`date`.
        """
        super().__init__(**kwargs)
        self.date = date
        self.rate = rate

    def serialize(self) -> dict[str, JSONValue]:
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["date"] = parseDate(data.get("date"))
        data["rate"] = parseFloat(data.get("rate"))
        return cls(**data)


class InstallmentPlan(BaseModel):
    """One installment plan the customer can choose from."""

    def __init__(
            self,
            numberOfRates: int | None = None,
            totalAmount: float | None = None,
            nominalInterestRate: float | None = None,
            effectiveInterestRate: float | None = None,
            interestAmount: float | None = None,
            minimumInstallmentFee: float | None = None,
            secciUrl: str | None = None,
            installmentRates: list[InstallmentRate] | None = None,
            **kwargs,
    ):
        """Create a new InstallmentPlan.

        :param numberOfRates: Duration of this plan in months.
        :param totalAmount: Total amount payable including interest.
        :param nominalInterestRate: Nominal interest rate in percent.
        :param effectiveInterestRate: Effective interest rate in percent.
            This value must be sent as ``effectiveInterestRate``
            with the authorize call of the payment.
        :param interestAmount: (optional) Interest included in :attr:`totalAmount`.
        :param minimumInstallmentFee: (optional) Minimum fee per rate.
        :param secciUrl: (optional) URL of the pre-contractual information
            (Standard European Consumer Credit Information) to show to the customer.
        :param installmentRates: The single rates of this plan.
        """
        super().__init__(**kwargs)
        if installmentRates is None:
            installmentRates = []
        self.numberOfRates = numberOfRates
        self.totalAmount = totalAmount
        self.nominalInterestRate = nominalInterestRate
        self.effectiveInterestRate = effectiveInterestRate
        self.interestAmount = interestAmount
        self.minimumInstallmentFee = minimumInstallmentFee
        self.secciUrl = secciUrl
        self.installmentRates = installmentRates

    def serialize(self) -> dict[str, JSONValue]:
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        if data.get("numberOfRates") is not None:
            data["numberOfRates"] = int(data["numberOfRates"])
        for key in (
                "totalAmount",
                "nominalInterestRate",
                "effectiveInterestRate",
                "interestAmount",
                "minimumInstallmentFee",
        ):
            data[key] = parseFloat(data.get(key))
        data["installmentRates"] = [
            InstallmentRate.fromDict(rate)
            for rate in data.get("installmentRates") or []
        ]
        return cls(**data)


class InstallmentPlans(BaseModel):
    """Response of the installment plans inquiry.

    .. seealso:: :meth:`unzer.UnzerClient.getPaylaterInstallmentPlans`
    """

    def __init__(
            self,
            inquiryId: str | None = None,
            amount: float | None = None,
            currency: str | None = None,
            expiresAt: datetime.datetime | None = None,
            plans: list[InstallmentPlan] | None = None,
            isSuccess: bool | None = None,
            isPending: bool | None = None,
            isResumed: bool | None = None,
            isError: bool | None = None,
            **kwargs,
    ):
        """Create a new InstallmentPlans.

        :param inquiryId: (original: id) Id of this inquiry (e.g. ``Tx-vyexxxzzy8p``).
            Required to create the :class:`unzer.model.PaylaterInstallment` payment type.
        :param amount: The amount the plans were calculated for.
        :param currency: ISO currency code.
        :param expiresAt: (optional) Expiry of this calculation.
        :param plans: The available plans.
        :param isSuccess: (optional) The calculation succeeded.
        :param isPending: (optional)
        :param isResumed: (optional)
        :param isError: (optional) The calculation failed.
        """
        super().__init__(**kwargs)
        if plans is None:
            plans = []
        self.inquiryId = inquiryId
        self.amount = amount
        self.currency = currency
        self.expiresAt = expiresAt
        self.plans = plans
        self.isSuccess = isSuccess
        self.isPending = isPending
        self.isResumed = isResumed
        self.isError = isError

    def serialize(self) -> dict[str, JSONValue]:
        raise NotImplementedError("No serialisation for response models.")

    @classmethod
    def fromDict(cls, data: dict[str, JSONValue]) -> t.Self:
        data = data.copy()
        data["inquiryId"] = data["id"]
        data["amount"] = parseFloat(data.get("amount"))
        # Unzer sends the expiry as unix timestamp (as string), in milliseconds --
        # the API reference shows seconds. parseTimestamp handles both.
        data["expiresAt"] = parseTimestamp(data.get("expiresAt"))
        data["plans"] = [InstallmentPlan.fromDict(plan) for plan in data.get("plans") or []]
        for key in ("isSuccess", "isPending", "isResumed", "isError"):
            data[key] = parseBool(data[key]) if key in data else None
        return cls(**data)
