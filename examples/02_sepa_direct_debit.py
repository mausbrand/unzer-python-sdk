#!/usr/bin/env python
"""Direct charge with SEPA direct debit.

One of the seven methods whose data the SDK sends itself, so no Payment Page and no
frontend component is involved. The payment type is created at Unzer as part of the
charge call.
"""

from _common import build_client, require_method

from unzer.model import PaymentRequest, SepaDirectDebit

# Official sandbox test data: docs.unzer.com/reference/test-data/
TEST_IBAN = "DE89370400440532013000"
TEST_BIC = "COBADEFFXXX"
TEST_HOLDER = "Maximilian Mustermann"


def main() -> None:
    client = build_client()
    require_method(client, "sepa-direct-debit")

    response = client.charge(PaymentRequest(
        paymentType=SepaDirectDebit(iban=TEST_IBAN, bic=TEST_BIC, holder=TEST_HOLDER),
        amount=12.34,
        currency="EUR",
        returnUrl="https://shop.example.com/return",
        orderId="example-sdd-1",
    ))

    if response.isSuccess:
        print(f"charged:       {response.transactionId}")
        print(f"payment:       {response.paymentId}")
        print(f"short id:      {response.processing.shortId}")
        print(f"creditor iban: {response.processing.iban}")
    elif response.isPending:
        # Not an error: the customer has to confirm somewhere first.
        print(f"pending, send the customer to: {response.redirectUrl}")

    payment = client.getPayment(response.paymentId)
    print(f"\nstate:    {payment.state.name}")
    print(f"charged:  {payment.amountCharged} of {payment.amountTotal}")
    for transaction in payment.transactions:
        print(f"  {transaction.action.name:10} {transaction.status.name:8} "
              f"{transaction.transactionId}")


if __name__ == "__main__":
    main()
