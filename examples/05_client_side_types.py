#!/usr/bin/env python
"""Paying with a payment type that was created in the browser.

Card, Klarna, PayPal, Apple Pay, Google Pay and others are not created server-side.
The Payment Page or Unzer's UI components collect the data in the browser, and your
backend only receives the resulting `typeId` -- which is why those classes carry no
fields. For cards this is deliberate: taking raw card data would make your integration
PCI-DSS liable.

Creating such a type server-side produces an empty resource that the provider rejects
later in the flow, with errors that look like SDK bugs but are not (Klarna answers
`COR.800.400.160 "Validation error at partner system"`).

So the backend side is short: wrap the id and charge it.
"""

import sys

from _common import build_client

from unzer.model import PaymentRequest, PaymentType


def charge_existing_type(client, payment_type: PaymentType, amount: float):
    """Charge a payment type the frontend already created."""
    return client.charge(PaymentRequest(
        paymentType=payment_type,
        amount=amount,
        currency="EUR",
        returnUrl="https://shop.example.com/return",
        orderId="example-client-side-1",
    ))


def main() -> None:
    client = build_client()

    type_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not type_id:
        print(__doc__)
        print("Usage: python 05_client_side_types.py <typeId>")
        print("\nA typeId looks like s-crd-abc123 (card) or s-kla-abc123 (Klarna).")
        print("Get one from the UI components; there is no server-side shortcut.")
        return

    # The short code in the id says which class to use -- no need to hardcode it.
    from unzer.model import PaymentGetResponse
    method = PaymentGetResponse.getPaymentTypeFromTypeId(type_id)
    payment_type = PaymentType.construct(method)(type_id)
    print(f"{type_id} -> {type(payment_type).__name__}")

    response = charge_existing_type(client, payment_type, 12.34)
    if response.isSuccess:
        print(f"charged: {response.transactionId}")
    elif response.isPending:
        # Card 3DS and Klarna both land here: the customer has to confirm.
        print(f"pending, redirect the customer to: {response.redirectUrl}")


if __name__ == "__main__":
    main()
