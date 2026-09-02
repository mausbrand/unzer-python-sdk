# AGENTS.md

Guidance for AI coding agents working in this repository. It covers what is specific to this
project — the general code style lives in `.editorconfig` and `tox.ini`, the contribution
workflow in `CONTRIBUTING.md`.

## What this project is

`unzer` is an **unofficial** Python SDK for the [Unzer](https://www.unzer.com) payment API.
Unzer publishes official SDKs for PHP and Java, plus an unmaintained Node/TypeScript one —
but none for Python. As far as we know this package is the only maintained Python SDK for
Unzer, so downstream users have no fallback. Treat breaking changes and half-working code
accordingly.

Known downstream consumer: [viur-shop](https://github.com/viur-framework/viur-shop) depends on
`unzer~=1.5` and uses both the client and the model classes directly. Renaming public API
means coordinating a release there.

## Verify against the API. Nothing else is authoritative.

**The running API is the only source of truth for this project.** Unzer's documentation is
wrong often enough that it cannot be trusted, and the official SDKs are wrong often enough
that they cannot be trusted either. Both are hints about where to look. Neither is evidence.

Before you implement a field, a required-ness, an endpoint version or an enum value: **call the
sandbox and look at what comes back.** Before you "fix" something because a docs page says it
is mandatory: call the sandbox and check whether the API agrees. If you cannot verify it, say
so in the commit message or the docstring instead of presenting it as fact.

Measured examples of the documentation and the SDKs being wrong — all of these were confirmed
by real sandbox calls, and every one of them would have produced a wrong change if the docs
had been believed:

| Claim | Reality |
|---|---|
| Klarna requires `termsAndConditionUrl` and `privacyPolicyUrl` | Works without them |
| Klarna requires a v2 basket | Runs on a v1 basket in production |
| The header is `x-CLIENTIP` | It is `CLIENTIP` |
| SEPA direct debit field is `accountHolder` | It is `holder` |
| Direct bank transfer short code is `opb` | It is `obp` |
| `types/openbanking-pis` takes an empty body | It takes `ibanCountry` |
| `EPS` is spelled `eps` | The API answers `EPS`, the path is `eps` |
| A keypair holds one config per payment type | It can hold several. One account has `card` twice: `MASTER`/`VISA` on one channel, `AMEX` on another — so the channel depends on the brand |
| `additionalTransactionData` has four fields (Java SDK docs) | The API has eight |
| `sandbox=True` needs the `sbx-api.unzer.com` host | Both hosts answer identically; the key prefix decides |
| Sending `billingAddress: ""` for a missing address | HTTP 400 `API.410.300.007`; `null` works |
| Paypage `action` comes back lower case | It comes back as `CHARGE` |
| `expiresAt` of the installment plans is a unix timestamp in seconds (`1735689599`, per the API reference) | It is **milliseconds** (13 digits). Reading it as seconds lands in the year 58608 and raises |
| The installment plans response is documented with seconds throughout | Mixed: `expiresAt` in ms, transaction dates as `YYYY-MM-DD HH:MM:SS` strings, rate dates as `YYYY-MM-DD` |
| One response uses one type per boolean | `card3ds` is a bool while `billingAddressRequired` is the string `"false"` — same response |
| A discount can be sent as its own negative basket item (a `voucher` line) | Both schemas reject negative item amounts — `API.600.200.131`, plus `API.600.410.018` on v1. A discount belongs in `amountDiscount` (v1) or `amountDiscountPerUnitGross` (v3), positive |
| The basket endpoint checks its own arithmetic | Only v3 does, to the cent (`API.600.410.062`). v1 accepts items that contradict `amountTotalGross`, and a charge does not compare the basket to the payment amount either — measured with Prepayment: amounts of 817.02, 726.24, 907.80 and 1.00 are all accepted against the same basket worth 817.02 |
| Any `returnUrl` the API accepts is fine for local development | A gateway in front of the API refuses `localhost`, `127.0.0.1` and private IPs with a **403 and an nginx HTML page** — the API never sees the request. Hostnames that merely *resolve* to 127.0.0.1 (`lvh.me`, `localtest.me`, `127-0-0-1.nip.io`) pass, so the block is on the string, not the resolved address |

### How to verify

Put a **sandbox** private key in a `.env` in the repository root (git-ignored) and run the
sandbox tests:

```bash
echo 'UNZER_PRIVATE_KEY=s-priv-...' > .env
pytest -m sandbox
```

Sandbox keys start with `s-priv-`, production keys with `p-priv-`. `tests/conftest.py` refuses
to run with anything that is not a sandbox key, because the suite creates real transactions on
whatever account it is pointed at. **Never point it at production**, and never commit a key.

Note that sandbox accounts differ in which payment methods they have enabled — an account
without `paylater-*` cannot verify the installment flow. Check `keypair/types` first.

### Where to look before calling

For finding out *what to try*, in this order:

1. **`github.com/unzerdev/php-sdk`** — `src/Resources/PaymentTypes/*.php`. The URL slug is the
   kebab-case class short name (`ResourceNameService::getClassShortNameKebapCase`).
   Use branch `main`; the GitHub tree API needs it explicitly. `develop` is **dead** (last
   commit 2024-02-07, 0 ahead / 96 behind `main`) — do not look there.
2. **`github.com/unzerdev/java-sdk`** — `paymenttypes/*.java` (`getResourceUrl()`) and
   `PaymentTypeEnum.java` for the short codes.
3. **`https://api.unzer.com/swagger-ui/api-docs`** — the full OpenAPI spec; the API reference
   page is only a ReDoc wrapper around it. Incomplete: `clicktopay` and `sofort` are missing
   although both exist. Still the best written source for `additionalTransactionData`.
4. `docs.unzer.com` — last, and only for prose and flow descriptions.

Where sources contradict each other, resolve it with a sandbox call and note in the docstring
which one turned out right — otherwise the next person cannot tell a decision from a mistake.

### Further sources worth knowing

```
Test data — for tests and examples/, never invent card numbers:
  https://docs.unzer.com/reference/test-cards/   # 3DS and frictionless PANs
  https://docs.unzer.com/reference/test-data/    # IBANs, logins, PIN keywords, 2FA triggers

Changelog — check before starting work on a resource:
  https://docs.unzer.com/news/                   # /news/articles/ itself returns 403

Mandatory field lists and step order, per payment method (treat as hints, not as truth):
  https://docs.unzer.com/payment-methods/invoice/accept-unzer-invoice-upl-server-side-only-integration/
  https://docs.unzer.com/payment-methods/installment/accept-unzer-installment-server-side-only-integration/
  https://docs.unzer.com/payment-methods/klarna/accept-klarna-server-side-only-integration/
  https://docs.unzer.com/payment-methods/direct-bank-transfer/manage-unzer-open-banking-payment/

CCD2 two-factor risk check — documented as a mandatory redirect flow for the paylater types,
not yet verified against the API:
  https://docs.unzer.com/ccd2-2fa/

Payment Page attribute keys, as a live generator:
  https://demo.unzer.com/demo/resources/paypage_manual.html

When a docs URL 404s — the site was restructured in April 2026:
  https://docs.unzer.com/sitemap.xml
```

`api-reference-docs.unzer.com/reference` is a second, **older** API reference (Readme.io,
OpenAPI 3.0.1, 111 paths against the Swagger spec's 151). Use it only as an archive for the
legacy `sofort` and `pis` types and the PayPal PATCH models; it has no download endpoint, the
spec sits as JSON inside the SSR HTML of every `/reference/*` page.

## Deliberate design decisions that look like gaps

**Payment types without payload fields are intentional.** `Card`, `Klarna`, `Ideal`,
`PayPal`, `Applepay`, `Googlepay`, `ClickToPay` and others carry no fields even though their
`types` endpoints accept some. These types are created client-side through the Payment Page or
the UI components; only the resulting `typeId` comes back to the backend, so a server-side
`createPaymentType()` with an empty body never occurs in those flows. For `Card` it is doubly
deliberate: accepting raw card data would make the integration PCI-DSS liable.

This has a consequence for testing: **these types cannot be exercised server-side.** Creating
one yields an empty resource that the provider rejects further down the flow — Klarna answers
`COR.800.400.160 "Validation error at partner system"`, which looks like an SDK bug and is not
one. The sandbox tests therefore only drive types whose fields the SDK actually sends (SEPA
direct debit, EPS, the paylater types, Wero, Direct Bank Transfer).

Do not add fields to these classes. Server-side fields belong only to types that are actually
created server-side — Installment, SEPA Direct Debit, Direct Bank Transfer.

**camelCase is the current public API, on purpose for now.** Method and attribute names mirror
the Unzer JSON payload (`getPayment`, `paymentId`, `amountTotalGross`). This is scheduled to
change to snake_case in 2.0, together with a move to dataclasses. Until then: do not rename
anything, and keep new *parameters* snake_case only where that is already the local convention
(`api_version`, `client_ip`, `additional_transaction_data`).

**Unzer offers no idempotency keys.** Neither OpenAPI spec contains an `Idempotency-Key`
header, and `docs.unzer.com` has no mention of idempotency at all. A retried `POST` can
therefore repeat a payment operation that already succeeded. Any change to the retry logic in
`UnzerClient._request` must keep that in mind: retrying after the request has been sent is a
double-charge risk, not a robustness feature.

**A keypair can configure the same payment type more than once.** Reading the payment method
configuration therefore needs a brand: `get_channel_id(brand="AMEX")`. Without it the first
entry wins, which is silently the wrong channel for every other brand. `get_configurations()`
returns all entries; `get_configuration()` keeps returning the first one for compatibility and
logs a warning when there is more than one.

Sandbox accounts also differ in which *fields* the keypair carries at all — `coreId` and
`merchantAddress` on one, `productType` and `unzerId` on another. Anything reading the keypair
must tolerate missing keys. And `allowCustomerTypes` is a comma-separated **string**
(`"B2B,B2C"`), not a list.

**An unknown enum value raises. There is no fallback anywhere.** It means this SDK is behind
the API, which is a defect worth seeing: `ValueError` names the offending value and points at
the parsing code, and the fix is to add the missing member.

A placeholder member would also be ambiguous, because `unknown` is a **real** value in this
API with a meaning of its own — `salutation: "unknown"` is what the API answers for a customer
whose salutation is not known. A same-named placeholder could not be told apart from it.

Do not make an enum tolerant via `_missing_` either. That applies to caller input as well, so
a typo in our own code silently turns into a placeholder — which is how
`PaymentPage(action="nonsense")` stopped failing once.

Which makes completeness the actual requirement: `Action` declares all nine transaction types
of the API — `authorize`, `preauthorize`, `charge`, `cancel-authorize`, `cancel-charge`,
`shipment`, `payout`, `chargeback`, `strong_customer_authentication` — even though this SDK can
only create two of them. A payment lists every transaction it holds, so knowing only those two
made `getPayment()` raise for every payment that had ever been cancelled, shipped or paid out.
If Unzer adds a tenth, that is a release of this SDK, not a fallback.

Every enum carries a `.. seealso::` link to the file it mirrors, so completeness is checkable
against the source instead of being a matter of memory. Where this SDK deliberately deviates
from its source, the docstring says so and why — `PaymentTypes` drops the `UNKNOWN` member that
the Java SDK uses as a parsing fallback. Deviating silently is how `Action` came to be missing
a type in the first place.

**Basket-level amounts are rounded to four decimals on serialisation**
(`unzer.utils.roundAmount`). The API takes `Decimal{10,4}`, and float arithmetic does not
cooperate: `12.3 - 10.0 - 2.3` is `8.88e-16`, which `json.dumps` writes in scientific
notation — not a number the API accepts. Amounts come back from the API as *strings* with
four decimals (`"5.5500"`).

`BasketItem.serialize` does **not** do this — measured, an item goes out as
`0.30000000000000004` next to a basket total rounded to `0.3`. That is an inconsistency,
not a design decision (#18), and it matters most where v3 reconciles the total against the
items to the cent.

**`Basket` intentionally supports two incompatible schemas.** v1 uses `amountTotalGross`, v3
uses `totalValueGross`; setting the latter switches the basket to the v3 endpoint. Do not
"clean this up" into one schema.

Which version a payment method needs is a recurring source of confusion, and the
documentation is not reliable here. Measured, the answer so far is that none of them
*needs* a particular one — what the column records is which schemas were seen to work,
not a requirement:

| Method | Verified in practice | What the docs claim |
|---|---|---|
| `paylater-installment` | **both** — sandbox authorize succeeds on v1 and on v3 | v3 |
| `klarna` | **both** — v1 in production use via viur-shop, v3 measured | v2 |
| `paylater-invoice` | not verified | v2 |
| everything else | v1 | v1 |

**Do not mix the schemas within one basket** — and note that only one direction fails
loudly. Measured: a v3 item in a v1 basket is accepted with a 201 and every item amount
stored as `0.0000`, while the basket-level total survives, so the basket looks plausible
and every line is worth nothing. A v1 item in a v3 basket is refused with
`API.600.410.051`. `Basket.isV3()` and `BasketItem.isV3()` decide independently and
nothing checks that they agree (#16). A basket is also only readable through the schema it
was created with — `API.600.410.024` otherwise — and the ids differ visibly: v1 gives
`s-bsk-72`, v3 a UUID.

**A basket can only be used once.** A second charge against the same `basketId` is refused with `API.330.200.152 "Resources: basket was used."`, so a retry after a failed authorize needs a new basket.

**Discounts belong in a discount field, not in a negative line item.** The obvious
shape — one item per article plus a `voucher` item carrying the negative discount, the
grosses adding up to the order total — is refused by both schemas
(`API.600.200.131 "Amount … has to be positive"`, and `API.600.410.018` on v1). Send the
discount as a positive value instead:

| | v1 | v3 |
|---|---|---|
| Field | `amountDiscount` — per line or per unit is **undecidable, and so far inconsequential**: nothing measured reads the value back out (see below) | `amountDiscountPerUnitGross`, **per unit** |
| Item amount | `amountGross` stays the pre-discount gross; the API stores both untouched | `amountPerUnitGross` minus the discount must stay positive |
| Total | not checked at all | `totalValueGross == sum((amountPerUnitGross - amountDiscountPerUnitGross) * quantity)`, exact to the cent (`API.600.410.062`) |
| `vat` per item | optional | mandatory (`API.600.410.052`) |

So a discount that exceeds a single line has to be spread over several items in v3,
while v1 swallows it. v3 names the offending line in `API.600.410.064` ("Basket item i1
'amountDiscountPerUnitGross' does not equal to 'amountPerUnitGross'") — but only if the
basket total stays positive; otherwise the negative total is refused first with the
generic `API.600.200.131`, which says nothing about the item. The v1 tolerance is not a
licence: a charge does not compare the basket to the payment amount, but the methods
that forward the basket to a partner system may. `tests/sandbox/test_live_api.py::TestBasket` holds all of this as executable evidence,
except the v1 per-line/per-unit question above.

**Nothing measured consumes `amountDiscount`.** The question was chased down the whole
chain with an item of `quantity=3`, gross 300.00 and `amountDiscount=10.00`, where the
two readings differ by 20.00:

* the v1 basket endpoint stores it and reconciles nothing;
* a charge does not compare the basket to the amount at all;
* Klarna's checkout lists the item by title only and takes its total from the authorize
  `amount` — 290.00 and 270.00 were both accepted and both displayed as sent;
* Unzer's Hosted Payment Page renders the line as `3x T-Shirt € 300,00`, i.e. plain
  `amountGross` with the discount nowhere, and its total likewise comes from the request,
  not from the basket.

So `amountDiscount` is stored and forwarded but not evaluated by anything reachable from
here, and the per-line/per-unit distinction has no observable effect. Worth knowing for
two reasons: the value cannot be used to make a basket "add up" for the customer, and a
line reduced by a discount is shown at its **undiscounted** gross next to a lower total,
with no label explaining the difference.

Basket v2 is not implemented (`Basket.apiVersion` only returns `v1` or `v3`), and so far
nothing has needed it. v2 and v3 share one schema, so if a method ever does require v2, the v3
model can build the body — only the endpoint version differs.

**Do not "fix" a working integration because the documentation says a field or version is
mandatory.** Unzer documents requirements that the API does not enforce. Two measured examples:
Klarna runs without the `termsAndConditionUrl`/`privacyPolicyUrl` that its page calls
mandatory, and it runs on a v1 basket. Check against a real sandbox call before changing
anything on the strength of a docs page.

## Code style

- PEP 8, except for the naming discussed above and the ignore list in `tox.ini`
  (`E121, E123, E126, E133, E226, E241, E242, E704, W503, W504, W505`).
- Lines up to 120 characters. Spaces, LF, UTF-8, trailing newline — see `.editorconfig`.
- Double quotes for strings, always.
- Multi-line dicts and lists: one `key: value` per line, trailing comma on the last entry.
- Type hints everywhere. Use `import typing as t`, built-in generics (`list[str]`, not
  `t.List[str]`) and `X | None` instead of `t.Optional[X]`. Do not repeat types in the
  docstring — the annotation is the single source of truth. Older modules still carry
  `# type:` comments and `:type x:` docstring lines; those are legacy, do not add more.
- Docstrings in Sphinx/reST format (`:param x:`, `:return:`, `.. seealso::`). No Google or
  NumPy style.
- **f-strings, without exception, in every line you write or touch** — including `logging`
  calls. Much of the older code uses `%` formatting; leave those lines alone unless you are
  changing them anyway, and never convert a line the other way round.
- **`X | None`, never a bare `X = None`.** Older signatures are full of implicit Optional
  (`client_ip: str = None`); do not add more, and fix the ones in lines you touch.
- Do not remove commented-out code, `TODO`/`ToDo` notes or debug helpers that you did not add
  yourself. If something looks obsolete, ask.
- Executable `.py` and `.sh` files carry the `+x` bit, in git too.

## Language

Code, comments, docstrings, commit messages and all repository files are written in English.
This is a public repository: it must contain no data, names or references from any customer
project — not in code, not in comments, not in commit messages, not as "adapted from X"
attribution. Everything here has to stand on its own.

## Where documentation goes

Four places, and the distinction matters:

| Target | Audience | Content |
|---|---|---|
| `README.md` | users of the package | install, auth, quickstart, error handling, supported payment methods |
| `docs/*.md` | users who need detail | per-topic reference that outgrew the README, e.g. `docs/payment-methods.md` |
| `AGENTS.md` | agents | this file — pitfalls, sources, decisions that look like bugs |
| `CONTRIBUTING.md` | contributors | workflow, style, release process |

`docs/superpowers/` is git-ignored working material: brainstorming output, design specs,
scratch notes. Nothing there is documentation, and nothing there should be committed.

**When a design document produces knowledge worth keeping, rewrite it into `docs/` — do not
commit the design document.** A file named `2026-08-05-some-feature-design.md` is a snapshot of
one decision on one day: the date makes it look stale the moment it is merged, nobody updates
it, and readers cannot tell whether it still describes the code. Permanent documentation is
named after its subject, carries no date, and is edited when the code changes.

## Commits and branches

- [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `chore:`,
  `refactor:`, `docs:`, `test:`, `cicd:`. Code identifiers in the subject may be written as
  `` `code` ``.
- Branch off before committing: `fix/*` for patch-level, `feat/*` for minor-level work.
- Pull request target: fixes (patch level) go against `main`, features (minor level) against
  `develop`.
- Do not add `Co-Authored-By` trailers.
- Commit only what belongs to the change at hand — no drive-by version bumps, no unrelated
  reformatting.
- Releases: bump `__version__`, commit as `chore: bump version to vX.Y.Z`, tag `vX.Y.Z`. The
  publish workflow triggers on the tag; a `v-test-*` prefix targets TestPyPI.

## Testing

Run the test suite before committing. Unit tests mock HTTP and never call the real API:

```bash
pip install -e ".[testing]"
pytest
pycodestyle src/                    # full tree, not just the diff
```

Tests marked `@pytest.mark.sandbox` talk to the Unzer sandbox and skip unless
`UNZER_PRIVATE_KEY` is set in the environment. Never commit keys — examples and tests read
them from environment variables, without exception.

Beware when writing tests against models: several `fromDict` implementations expect the exact
response shape of the API, so use real captured payloads as fixtures rather than hand-written
minimal dicts.

## Things that are easy to get wrong here

- `PaymentType.method` is the short code (`crd`), `method_name` is the URL slug (`card`). The
  naming is unfortunate and inherited from Unzer, which is inconsistent about it too — the
  same method appears as `EPS` and as `eps` depending on the endpoint.
- Responses are parsed by `fromDict(data, client)`; request models use `serialize()`. Response
  models raise `NotImplementedError` from `serialize()` by design.
- `PaymentTransaction` derives its ids by parsing the transaction URL with a regex, because
  the API does not return them as separate fields. Changing `UnzerClient.endpoint` therefore
  affects parsing.
- Errors can arrive with a 2xx status code and an `errors` list in the body — Unzer documents
  this explicitly. Do not treat HTTP 200 as success without checking `isError`.
- Not every 4xx body is JSON. The gateway in front of the API answers with an HTML page,
  so `_request` builds an `ErrorResponse` from the status and the raw text instead of
  parsing it — a bare `JSONDecodeError` from inside the SDK hides both and reads like an
  SDK bug. The known trigger is a `returnUrl` on localhost or a private IP.
- `logger.debug` output contains full request payloads, including IBANs and dates of birth.
  Do not add payload logging above DEBUG level.
