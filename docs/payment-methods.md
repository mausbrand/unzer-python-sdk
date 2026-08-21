# Payment methods

Which payment methods this SDK covers, how their data reaches Unzer, and which
peculiarities each one carries. Everything here is measured against the sandbox unless
marked otherwise — Unzer's documentation is not reliable on these points, see
[AGENTS.md](../AGENTS.md).

## Two ways a payment type is created

This is the distinction that explains most of the code, and most of the confusion.

**Server-side.** Your backend sends the payment data (an IBAN, a BIC) to
`POST /v1/types/<slug>` and gets a `typeId` back. Seven of the 24 methods work this way,
and their classes carry the corresponding fields.

**Client-side.** The Payment Page or one of Unzer's
[UI components](https://docs.unzer.com/online-payments/ui-component/) collects the data
in the browser, sends it to Unzer directly, and hands your backend the finished
`typeId`. The remaining 17 methods work this way, and their classes deliberately carry
**no fields** — there is nothing for the server to send.

For cards this is not just a convention: accepting raw card numbers on your own server
would put your integration under PCI-DSS obligations. The same reasoning applies to
Apple Pay and Google Pay, whose payload is a signed token that only the browser or the
wallet can produce.

**Consequence for the SDK:** creating a client-side type server-side produces an empty
resource. The call itself succeeds, and the failure surfaces much later, during the
authorization, as an error from the provider that looks like an SDK bug — Klarna answers
`COR.800.400.160 "Validation error at partner system"`. If you are debugging that, check
where the `typeId` came from.

## The methods

`method_name` is the slug in the `types/` path, `method` the short code that appears in
a type id (`s-crd-abc123`). Both are enums on the class: `Card.method_name.value` is
`"card"`, `Card.method.value` is `"crd"`.

| Class | Slug | Code | Created | Fields |
|---|---|---|---|---|
| `Alipay` | `alipay` | `ali` | client | — |
| `Applepay` | `applepay` | `apl` | client | — |
| `Bancontact` | `bancontact` | `bct` | server | `holder` (optional) |
| `Card` | `card` | `crd` | client | — (PCI-DSS) |
| `ClickToPay` | `clicktopay` | `ctp` | client | — |
| `Eps` | `eps` | `eps` | server | `bic` (optional) |
| `Googlepay` | `googlepay` | `gop` | client | — |
| `Ideal` | `ideal` | `idl` | client | — |
| `Klarna` | `klarna` | `kla` | client | — |
| `OpenbankingPis` | `openbanking-pis` | `obp` | server | `ibanCountry` |
| `PayPal` | `paypal` | `ppl` | client | — |
| `PayU` | `payu` | `pyu` | client | — |
| `PaylaterDirectDebit` | `paylater-direct-debit` | `pdd` | server | `iban`, `holder`, `country` |
| `PaylaterInstallment` | `paylater-installment` | `pit` | server | `inquiryId`, `numberOfRates`, `iban`, `country`, `holder` |
| `PaylaterInvoice` | `paylater-invoice` | `piv` | client | — |
| `PostFinanceCard` | `post-finance-card` | `pfc` | client | — |
| `PostFinanceEfinance` | `post-finance-efinance` | `pfe` | client | — |
| `Prepayment` | `prepayment` | `ppy` | client | — |
| `Przelewy24` | `przelewy24` | `p24` | client | — |
| `SepaDirectDebit` | `sepa-direct-debit` | `sdd` | server | `iban`, `bic`, `holder` |
| `Sofort` | `sofort` | `sft` | client | — (discontinued by Unzer) |
| `Twint` | `twint` | `twt` | client | — |
| `Wechatpay` | `wechatpay` | `wcp` | client | — |
| `Wero` | `wero` | `wro` | server | `walletId` |

## Not implemented, on purpose

**giropay** — discontinued by Unzer, deprecated in their PHP SDK 4.0.0 and no longer
listed under their payment methods. The short code `gro` still exists in `PaymentTypes`
so that older payments read back, but there is no class.

**The secured legacy types** — `invoice`, `invoice-secured`, `installment-secured`,
`sepa-direct-debit-secured`. Deprecated, only relevant for old contracts. Their short
codes are in `PaymentTypes` for the same reason.

A payment using one of these still reads back: `PaymentType.construct()` builds a
placeholder class on the fly. The placeholder cannot create a new payment type — asking
it for its slug raises `NotImplementedError` with an explanation rather than an obscure
`AttributeError`.

## Method-specific notes

### Installment (`paylater-installment`)

The only method with a mandatory order of calls:

1. `getPaylaterInstallmentPlans(amount, currency, country)` — the plans have to be shown
   to the customer, because the payment type needs the `inquiryId` from this response.
2. Create customer and a **v3 basket** (set `totalValueGross`, not `amountTotalGross`).
3. `createPaymentType(PaylaterInstallment(inquiryId=…, numberOfRates=…))`.
4. Optionally `riskCheckPaylaterInstallment(request)` — evaluates the customer before the
   order is placed, so a rejection reaches them during checkout rather than after.
5. `authorize(request)`.

`expiresAt` in the plans response is a unix timestamp in **milliseconds**, though the API
reference shows seconds. The `CLIENTIP` header is required for the risk checks — pass
`client_ip` to the client. Note the API reference calls that header `x-CLIENTIP`; the API
wants `CLIENTIP`, which is also what the PHP and Java SDKs send.

### Klarna

Runs on a **v1 basket** and without `termsAndConditionUrl`/`privacyPolicyUrl`, both of
which the documentation lists as mandatory. Verified in production use. Klarna cannot be
charged directly: authorize first, then charge after the customer returns from the
redirect (typically on shipment).

### Direct bank transfer (`openbanking-pis`)

Settlement is deferred. After the customer pays, the payment is `completed` while the
charge stays `pending` — for up to seven working days. Only then does it become `success`,
or `failed` with `SETTLEMENT_TIMEOUT`. A failed settlement can still recover to `success`
afterwards. **Do not ship on `charge.pending`.**

Note there are two distinct types: `openbanking-pis` (code `obp`, takes `ibanCountry`) and
a legacy `pis` (takes `iban`/`bic`/`holder`). Only the former is implemented.

### Cards

3DS is configured per keypair, and `card3ds` on the request can override it. A keypair may
hold **several configurations for `card`** — one observed account has `MASTER`/`VISA` on
one channel and `AMEX` on another, with different currencies. Ask for the channel by brand:

```python
Card(client=client).get_channel_id(brand="AMEX")
```

Without the brand you get the first entry, which is silently the wrong channel for every
other brand.

## Where these facts come from

Slugs and short codes are cross-checked against the official SDKs, because the OpenAPI
spec is incomplete — `clicktopay` and `sofort` are missing from it although both exist:

- `unzerdev/php-sdk`, `src/Resources/PaymentTypes/*.php` — the slug is the kebab-case
  class short name
- `unzerdev/java-sdk`, `PaymentTypeEnum.java` — the short codes
- `unzerdev/integration-core`, `PaymentMethodTypes.php` — the slug list

Everything about actual behaviour is measured against the sandbox. Where a source turned
out wrong, the docstring in the code says which one was followed.
