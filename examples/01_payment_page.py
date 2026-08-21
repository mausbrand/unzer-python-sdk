#!/usr/bin/env python
"""Hosted Payment Page -- the shortest complete flow.

Unzer hosts the page, the customer picks a payment method there, and no card data
ever reaches your server. Works for every payment method the account has enabled.
"""

from _common import build_client

from unzer.model import Action, PaymentPage


def main() -> None:
    client = build_client()

    page = client.createPaymentPage(PaymentPage(
        action=Action.CHARGE,          # or Action.AUTHORIZE to capture later
        amount=12.34,
        currency="EUR",
        returnUrl="https://shop.example.com/return",
        orderId="example-paypage-1",
        shopName="Example Shop",
        shopDescription="A single t-shirt",
    ))

    print(f"payPageId:   {page.payPageId}")
    print(f"paymentId:   {page.paymentId}")
    print(f"redirect to: {page.redirectUrl}")

    # After the customer returns, ask the API what happened. Never decide this from
    # the return URL alone -- it is under the customer's control.
    payment = client.getPayment(page.paymentId)
    print(f"\nstate now:   {payment.state.name}")
    print(f"charged:     {payment.amountCharged} {payment.currency}")
    print("A fresh page sits in CREATE until the customer engages with it.")


if __name__ == "__main__":
    main()
