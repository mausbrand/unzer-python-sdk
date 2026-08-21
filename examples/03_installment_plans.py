#!/usr/bin/env python
"""Unzer Installment: fetch the plans, then run the optional risk check.

Order matters here. The plans have to be shown to the customer before anything else,
because the payment type needs the `inquiryId` of the plan they picked. Installment
also requires a v3 basket and a customer with an address.
"""

from _common import build_client, require_method

from unzer.model import (
    Address,
    Basket,
    BasketItem,
    Customer,
    ErrorResponse,
    PaylaterInstallment,
    PaymentRequest,
)

AMOUNT = 100.0


def main() -> None:
    client = build_client()
    require_method(client, "paylater-installment")

    # 1. Which plans does the customer have to choose from?
    plans = client.getPaylaterInstallmentPlans(
        amount=AMOUNT, currency="EUR", country="DE", customerType="B2C",
    )
    print(f"inquiryId: {plans.inquiryId}")
    for plan in plans.plans:
        print(f"  {plan.numberOfRates:2}x  total {plan.totalAmount:>8}  "
              f"effective {plan.effectiveInterestRate}%")
    if not plans.plans:
        print("No plans offered for this amount.")
        return

    chosen = plans.plans[0]

    # 2. Customer and basket. Installment needs the v3 basket schema, which the
    #    Basket model selects as soon as totalValueGross is set.
    customer = client.createOrUpdateCustomer(Customer(
        firstname="Maximilian", lastname="Mustermann", salutation="mr",
        birthDate="1980-11-22", email="maximilian.mustermann@example.com",
        billingAddress=Address(
            firstname="Maximilian", lastname="Mustermann",
            street="Hugo-Junkers-Str. 3", zipCode="60386",
            city="Frankfurt am Main", country="DE",
        ),
    ))
    basket = client.createBasket(Basket(
        totalValueGross=AMOUNT, currencyCode="EUR", orderId="example-installment-1",
        basketItems=[BasketItem(
            title="Custom print t-shirt", quantity=1, vat=19,
            amountPerUnitGross=AMOUNT, basketItemReferenceId="item-1", type="goods",
        )],
    ))

    payment_type = client.createPaymentType(PaylaterInstallment(
        inquiryId=plans.inquiryId,
        numberOfRates=chosen.numberOfRates,
        iban="DE89370400440532013000",
        holder="Maximilian Mustermann",
        country="DE",
    ))
    print(f"\npayment type: {payment_type.key}")

    request = PaymentRequest(
        paymentType=payment_type, amount=AMOUNT, currency="EUR",
        returnUrl="https://shop.example.com/return",
        customerId=customer.key, basketId=basket.key,
        orderId="example-installment-1",
        effectiveInterestRate=chosen.effectiveInterestRate,
    )

    # 3. Optional: ask before placing the order, so the customer learns about a
    #    rejection while still in the checkout.
    try:
        result = client.riskCheckPaylaterInstallment(request)
        print(f"risk check passed: {result}")
    except ErrorResponse as error:
        print("risk check declined:")
        for entry in error.errors:
            print(f"  {entry.code}: {entry.merchantMessage}")
        return

    print("\nAuthorize next -- left out here so the example does not place an order.")


if __name__ == "__main__":
    main()
