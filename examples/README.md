# Examples

Runnable scripts, one flow each. They read the credentials from the environment:

```bash
export UNZER_PRIVATE_KEY=s-priv-...
export UNZER_PUBLIC_KEY=s-pub-...
python examples/01_payment_page.py
```

**Sandbox keys only** (`s-priv-…`). Every script refuses to start with a production key,
because they all create real transactions on whatever account the key belongs to.

| Script | Flow |
|---|---|
| `01_payment_page.py` | hosted Payment Page — works for every payment method |
| `02_sepa_direct_debit.py` | direct charge, server-side payment type |
| `03_installment_plans.py` | fetch installment plans and run the risk check |
| `04_webhooks.py` | register, list and delete webhooks |
| `05_client_side_types.py` | working with a `typeId` that came from the frontend |
| `06_probe_field_limits.py` | measure the field length limits the API enforces |
| `07_probe_b2b_customer.py` | measure what the API enforces for B2B customers (`companyInfo`) |

Two things to know before running them.

**`06` and `07` are measuring tools, not flows.** `06` binary-searches the longest value each
field accepts and prints the boundary; the numbers in `MAX_LENGTHS` come from it, because the
documented ones were wrong for several fields. `07` sends one B2B customer per case and shows
what the API refused or stored; the rules in `CompanyInfo` come from it. Neither sends anything
without `--execute`.

**Not every account can do everything.** Sandbox accounts differ in which payment methods are
enabled — `03` needs `paylater-installment`. Each script checks and tells you if the account
cannot do it. Use `keypair/types` to see what yours has.

**Use the official test data.** Card numbers, IBANs and the logins for redirect flows are
documented at [docs.unzer.com/reference/test-data](https://docs.unzer.com/reference/test-data/)
and [test-cards](https://docs.unzer.com/reference/test-cards/). Invented numbers get declined.
