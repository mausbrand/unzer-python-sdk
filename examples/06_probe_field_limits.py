#!/usr/bin/env python
"""Measure the field length limits the API actually enforces.

The docstrings in this SDK used to state limits taken from Unzer's documentation,
and several of them were wrong -- `street` is documented as 50 and enforced at 64.
So the numbers in `MAX_LENGTHS` come from this probe instead: it binary-searches
the boundary per field against the sandbox and prints what it found.

Run it again whenever a limit is in doubt, or to find the limit of a field that has
none declared yet.

It works on the serialized payload and sends it with `client.request`, deliberately
bypassing the models. An address has no `firstname` on the wire -- it has one `name`
that the model builds from two attributes -- so probing through `Address` would
measure the model's joining rather than the API's limit. The customer is the other
way round and sends the two names separately; both are reachable here because the
payload is built by hand.
"""
from __future__ import annotations

import argparse
import itertools
import typing as t
import uuid

from _common import build_client

import unzer

#: Upper bound for the search. No sane field accepts more than this -- the OpenAPI
#: spec documents 256 for the ``companyInfo`` fields, so the bound sits above that.
SEARCH_CEILING: t.Final[int] = 1000

#: Serialized field name -> where it sits: on the customer, in its addresses, in its
#: ``companyInfo`` or in the owner inside that. The last two are written as dotted
#: paths, because ``firstname`` exists on the customer and on the owner alike.
FIELDS: t.Final[dict[str, str]] = {
    "firstname": "customer",
    "lastname": "customer",
    "company": "customer",
    "name": "address",
    "street": "address",
    "zip": "address",
    "city": "address",
    "address.company": "address",
    "companyInfo.commercialRegisterNumber": "companyInfo",
    "companyInfo.function": "companyInfo",
    "companyInfo.commercialSector": "companyInfo",
    "companyInfo.companyType": "companyInfo",
    "companyInfo.owner.firstname": "owner",
    "companyInfo.owner.lastname": "owner",
}

#: Fields the API wants to look like a number rather than a word.
NUMERIC_FIELDS: t.Final[frozenset[str]] = frozenset({"zip"})


class Rejected(Exception):
    """The API refused the payload; carries the error codes it reported."""

    def __init__(self, codes: list[str], messages: list[str]) -> None:
        super().__init__(", ".join(codes))
        self.codes = codes
        self.messages = messages


def filler(field: str, length: int) -> str:
    """Build a value of exactly `length` characters for `field`.

    One repeated character class, so nothing but the length can upset a validator.

    :param field: The field the value is for.
    :param length: The desired length.
    :return: A string of that length.
    """
    alphabet = "0123456789" if field in NUMERIC_FIELDS else "abcdefghijklmnopqrstuvwxyz"
    return "".join(itertools.islice(itertools.cycle(alphabet), length))


def payload(field: str, length: int) -> dict[str, t.Any]:
    """Build a valid customer payload with `field` stretched to `length`.

    :param field: The serialized field to stretch.
    :param length: How long to make it.
    :return: The request body for ``POST /v1/customers``.
    """
    address = {"name": "Probe Tester", "street": "Teststrasse 1", "state": "",
               "zip": "44135", "city": "Dortmund", "country": "DE"}
    customer = {
        "firstname": "Probe", "lastname": "Tester", "id": "",
        "salutation": "mr", "company": "", "customerId": f"probe-{uuid.uuid4()}",
        "birthDate": "1980-01-01", "email": "probe@example.org",
        "phone": "", "mobile": "",
    }
    owner = {"firstname": "Probe", "lastname": "Tester", "birthdate": "1980-01-01"}
    # A registered company with an owner, so that every companyInfo field has a
    # valid baseline to stretch -- a registered one without a register number is
    # refused (API.410.100.110).
    company_info = {
        "registrationType": "registered", "commercialRegisterNumber": "HRB 12345",
        "function": "OWNER", "commercialSector": "OTHER", "companyType": "company",
        "owner": owner,
    }
    value = filler(field, length)
    leaf = field.rsplit(".", 1)[-1]
    target = {"customer": customer, "address": address,
              "companyInfo": company_info, "owner": owner}[FIELDS[field]]
    target[leaf] = value
    body = {**customer, "billingAddress": address, "shippingAddress": address}
    if FIELDS[field] in {"companyInfo", "owner"}:
        body["company"] = "Probe GmbH"
        body["companyInfo"] = company_info
    return body


def try_length(client: unzer.UnzerClient, field: str, length: int, *, execute: bool) -> None:
    """Send one customer and report whether the API accepted it.

    :param client: The client to send with.
    :param field: The serialized field to stretch.
    :param length: How long to make it.
    :param execute: Perform the call; otherwise only print what would be sent.
    :raises Rejected: When the API answered with a validation error.
    """
    if not execute:
        print(f"  DRY-RUN would POST /v1/customers with {field}={length} chars")
        return

    try:
        client.request("customers", "POST", payload(field, length))
    except unzer.model.ErrorResponse as err:
        raise Rejected([e.code for e in err.errors],
                       [e.merchantMessage for e in err.errors]) from err


def probe(client: unzer.UnzerClient, field: str, *, execute: bool) -> dict[str, t.Any]:
    """Binary-search the longest accepted value for one field.

    :param client: The client to send with.
    :param field: The serialized field to stretch.
    :param execute: Perform real calls.
    :return: The last accepted and first rejected length, plus the error codes.
    """
    # Dotted fields already name their place; the others get it prefixed.
    label = field if "." in field else f"{FIELDS[field]}.{field}"
    print(f"--- probing {label} ---")
    low, high = 1, SEARCH_CEILING
    last_ok: int | None = None
    first_bad: int | None = None
    codes: list[str] = []
    messages: list[str] = []

    # Confirm the ceiling is rejected at all; without that there is no boundary to find.
    try:
        try_length(client, field, high, execute=execute)
    except Rejected as rejection:
        first_bad, codes, messages = high, rejection.codes, rejection.messages
    else:
        print(f"  {high} chars still accepted -- no limit below {SEARCH_CEILING}")
        return {"field": field, "last_ok": high, "first_bad": None,
                "codes": [], "messages": []}

    while low < high:
        mid = (low + high) // 2
        try:
            try_length(client, field, mid, execute=execute)
        except Rejected as rejection:
            first_bad, codes, messages = mid, rejection.codes, rejection.messages
            high = mid
        else:
            last_ok = mid
            low = mid + 1

    return {"field": field, "last_ok": last_ok, "first_bad": first_bad,
            "codes": codes, "messages": messages}


def main() -> None:
    """Probe every configured field and print a summary table."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--field", action="append", choices=sorted(FIELDS),
                        help="limit the probe to these fields (default: all)")
    parser.add_argument("--execute", action="store_true",
                        help="actually call the sandbox (default: dry-run)")
    args = parser.parse_args()

    if not args.execute:
        print("DRY-RUN -- no requests are sent. Pass --execute to measure for real.\n")

    client = build_client()
    fields = tuple(args.field) if args.field else tuple(FIELDS)
    results = [probe(client, field, execute=args.execute) for field in fields]

    print("\n=== measured limits (POST /v1/customers) ===")
    print(f"{'field':<36} {'max accepted':>12} {'first rejected':>15}  codes")
    for result in results:
        print(f"{result['field']:<36} {result['last_ok']!s:>12} "
              f"{result['first_bad']!s:>15}  {','.join(result['codes'])}")
    for result in results:
        if result["messages"]:
            print(f"  {result['field']}: {result['messages'][0]}")


if __name__ == "__main__":
    main()
