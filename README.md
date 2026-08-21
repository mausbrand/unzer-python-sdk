<div align="center">
    <h1>unzer-python-sdk</h1>
    <a href="https://pypi.org/project/unzer/">
        <img alt="Badge showing current PyPI version" title="PyPI" src="https://img.shields.io/pypi/v/unzer">
    </a>
    <a href="LICENSE">
        <img src="https://img.shields.io/github/license/mausbrand/unzer-python-sdk" alt="Badge displaying the license" title="License badge">
    </a>
    <br>
    An unofficial python SDK for the payment service <a href="https://www.unzer.com">Unzer</a>.
</div>

> **Unofficial.** This package is not built or endorsed by Unzer. Unzer publishes SDKs for
> [PHP](https://github.com/unzerdev/php-sdk) and [Java](https://github.com/unzerdev/java-sdk),
> but none for Python.

## Requirements

Python 3.11 or newer. The only runtime dependency is
[requests](https://pypi.org/project/requests/).

## Installation

```bash
pip install unzer
```

## Authentication

Unzer authenticates with the **private key** of a keypair, sent as the username of HTTP basic
auth. Which environment a request reaches is decided by the key itself, not by the host:

| Prefix | Environment |
|---|---|
| `s-priv-…` | sandbox |
| `p-priv-…` | production |

```python
import unzer

client = unzer.UnzerClient(
    private_key="s-priv-...",
    public_key="s-pub-...",
    sandbox=True,     # informational: does not change the endpoint, see below
)
```

`sandbox` does not switch hosts — `api.unzer.com` serves both environments. Keep it accurate
anyway: consumers need to know which mode they are in, not least because the redirect URLs
Unzer returns differ (`sbx-payment.unzer.com` versus `payment.unzer.com`).

Never hardcode keys. The examples in [`examples/`](examples) read them from the environment.

## Quickstart

A Payment Page is the shortest complete flow: Unzer hosts the page, the customer picks a
method there, and you never touch card data.

```python
import os
import unzer
from unzer.model import Action, PaymentPage

client = unzer.UnzerClient(
    private_key=os.environ["UNZER_PRIVATE_KEY"],
    public_key=os.environ["UNZER_PUBLIC_KEY"],
    sandbox=True,
)

page = client.createPaymentPage(PaymentPage(
    action=Action.CHARGE,
    amount=12.34,
    currency="EUR",
    returnUrl="https://shop.example.com/return",
    orderId="my-order-1",
    shopName="Example Shop",
))

print(page.redirectUrl)   # send the customer here
print(page.paymentId)     # keep this to check the payment later
```

When the customer comes back, ask the API what happened — never trust the return URL alone:

```python
payment = client.getPayment(page.paymentId)
print(payment.state)          # CREATE right after init, then PENDING / COMPLETED / ...
print(payment.amountCharged)
```

A payment starts out as `PaymentState.CREATE` and only becomes `PENDING` once the customer
engages with the page, so treat anything but `COMPLETED` as "not paid yet".

### Charging a payment method directly

Methods whose data the SDK can send itself — see the table below — work without a Payment Page:

```python
from unzer.model import PaymentRequest, SepaDirectDebit

response = client.charge(PaymentRequest(
    paymentType=SepaDirectDebit(
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        holder="Maximilian Mustermann",
    ),
    amount=12.34,
    currency="EUR",
    returnUrl="https://shop.example.com/return",
    orderId="my-order-2",
))

if response.isSuccess:
    print(response.transactionId, response.processing.shortId)
elif response.isPending:
    print("customer has to confirm:", response.redirectUrl)
```

The payment type is created at Unzer as part of this call if it has no `key` yet.

## Testing against the sandbox

Use a `s-priv-` key and the
[official test data](https://docs.unzer.com/reference/test-data/) — test cards, IBANs and the
logins for the redirect flows. Do not invent card numbers; they will be declined.

## Error handling

Any 4xx response raises `ErrorResponse`. It carries the whole error payload, and Unzer's
`merchantMessage` is the field worth logging — `customerMessage` is meant to be shown to the
customer and is translated according to the `language` you pass to the client.

```python
from unzer.model import ErrorResponse

try:
    client.charge(payment_request)
except ErrorResponse as error:
    print(error.statusCode)          # 400
    print(error.errorId)             # s-err-... , quote this to Unzer support
    for entry in error.errors:
        print(entry.code)            # API.320.200.145
        print(entry.merchantMessage) # Basket is already in use.
        print(entry.customerMessage)
```

Two things to know. A response can carry `errors` **with a 2xx status code**, which the SDK
also raises for. And a pending payment is not an error: `isPending` with a `redirectUrl` means
the customer has to confirm somewhere, and you have to follow up with `getPayment()`.

## Supported payment methods

All 24 payment methods Unzer currently offers. `method_name` is the slug in the `types/` path,
`method` the short code that appears in a type id such as `s-crd-abc123`.

Seven of them accept data from the server; the rest are created **client-side** through the
Payment Page or Unzer's UI components, which hand you a ready `typeId`. Those classes
deliberately carry no fields — for cards, accepting raw card data would make your integration
PCI-DSS liable.

| Class | `types/` slug | Code | Fields the SDK sends |
|---|---|---|---|
| `Alipay` | `alipay` | `ali` | — |
| `Applepay` | `applepay` | `apl` | — |
| `Bancontact` | `bancontact` | `bct` | `holder` |
| `Card` | `card` | `crd` | — |
| `ClickToPay` | `clicktopay` | `ctp` | — |
| `Eps` | `eps` | `eps` | `bic` |
| `Googlepay` | `googlepay` | `gop` | — |
| `Ideal` | `ideal` | `idl` | — |
| `Klarna` | `klarna` | `kla` | — |
| `OpenbankingPis` | `openbanking-pis` | `obp` | `ibanCountry` |
| `PayPal` | `paypal` | `ppl` | — |
| `PayU` | `payu` | `pyu` | — |
| `PaylaterDirectDebit` | `paylater-direct-debit` | `pdd` | `iban`, `holder`, `country` |
| `PaylaterInstallment` | `paylater-installment` | `pit` | `inquiryId`, `numberOfRates`, `iban`, `country`, `holder` |
| `PaylaterInvoice` | `paylater-invoice` | `piv` | — |
| `PostFinanceCard` | `post-finance-card` | `pfc` | — |
| `PostFinanceEfinance` | `post-finance-efinance` | `pfe` | — |
| `Prepayment` | `prepayment` | `ppy` | — |
| `Przelewy24` | `przelewy24` | `p24` | — |
| `SepaDirectDebit` | `sepa-direct-debit` | `sdd` | `iban`, `bic`, `holder` |
| `Sofort` | `sofort` | `sft` | — |
| `Twint` | `twint` | `twt` | — |
| `Wechatpay` | `wechatpay` | `wcp` | — |
| `Wero` | `wero` | `wro` | `walletId` |

`Sofort` and `giropay` are being discontinued by Unzer; the deprecated legacy types
(`invoice`, `invoice-secured`, `installment-secured`, `sepa-direct-debit-secured`) are not
implemented.

## What the SDK covers

| | |
|---|---|
| Resources | customers, baskets (v1 and v3), payment types, payment pages, webhooks, keypair |
| Transactions | `authorize`, `charge` |
| Extras | installment plans, installment risk check, additional transaction data |

**Not implemented yet:** cancellations and refunds, shipments, payouts, recurring payments,
the metadata resource, chargeback retrieval, and Payment Page v2 / LinkPay. A payment that was
cancelled or shipped elsewhere still reads back correctly — the transaction types are known,
they just cannot be created here.

## Logging

Everything logs below `unzer-sdk`:

```python
import logging
logging.getLogger("unzer-sdk").setLevel(logging.DEBUG)
```

**`DEBUG` logs complete request and response bodies**, including IBANs, card holder names and
dates of birth. Do not enable it in production without knowing where those logs end up.

## Documentation

This README is the SDK documentation. For the API itself, see Unzer's own:

- [API basics](https://docs.unzer.com/server-side-integration/api-basics/) — auth, errors, notifications
- [API reference](https://api.unzer.com/api-reference/index.html)
- [Payment methods](https://docs.unzer.com/payment-methods/) — the flow each method requires
- [Test data](https://docs.unzer.com/reference/test-data/)

## Development

```bash
uv sync --extra testing          # or: pip install -e ".[testing]"
uv run pytest                    # unit tests, no network
uv run pycodestyle src/ tests/
```

The sandbox tests are opt-in and need a sandbox key:

```bash
echo 'UNZER_PRIVATE_KEY=s-priv-...' > .env    # git-ignored
uv run pytest -m sandbox
```

They create real resources on whatever account the key belongs to, so the suite refuses to run
with anything but a `s-priv-` key. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and
[AGENTS.md](AGENTS.md) for the pitfalls this API has in store.

## License

[MIT](LICENSE)
