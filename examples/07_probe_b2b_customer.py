#!/usr/bin/env python
"""Measure what the API enforces for B2B customers (``companyInfo``).

The PHP SDK, the Java SDK, the OpenAPI spec and docs.unzer.com disagree on which
``companyInfo`` fields are mandatory, which values are valid and what the API sends
back. This probe settles it: every case changes one thing against a baseline that
the API accepts, sends it to ``POST /v1/customers`` and, when accepted, reads the
customer back to show what was stored.

Like ``06_probe_field_limits.py`` it works on hand-built payloads and bypasses the
models, because the models are what this probe is meant to inform.

Dry-run by default; ``--execute`` performs the calls. ``--dump DIR`` writes every
customer the API returned as JSON, for use as test fixtures.
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import typing as t
import uuid

from _common import build_client

import unzer

#: Marks a key that a case removes from the payload.
DROP: t.Final[object] = object()


def base_payload(registration_type: str) -> dict[str, t.Any]:
    """Build a B2B customer the way the PHP SDK's ``CustomerFactory`` does.

    :param registration_type: ``registered`` or ``not_registered``.
    :return: The request body for ``POST /v1/customers``.
    """
    address = {
        "name": "Probe Tester",
        "street": "Teststrasse 1",
        "state": "",
        "zip": "44135",
        "city": "Dortmund",
        "country": "DE",
    }
    company_info: dict[str, t.Any] = {
        "registrationType": registration_type,
        "function": "OWNER",
        "commercialSector": "OTHER",
    }
    if registration_type == "registered":
        company_info["commercialRegisterNumber"] = "HRB 12345"
    return {
        "firstname": "Probe",
        "lastname": "Tester",
        "salutation": "mr",
        "company": "Probe GmbH",
        "customerId": f"probe-{uuid.uuid4()}",
        "birthDate": "1980-01-01",
        "email": "probe@example.org",
        "billingAddress": address,
        "shippingAddress": copy.deepcopy(address),
        "companyInfo": company_info,
    }


def apply(payload: dict[str, t.Any], changes: dict[str, t.Any]) -> dict[str, t.Any]:
    """Apply dotted-path changes to a copy of `payload`.

    :param payload: The baseline.
    :param changes: ``{"companyInfo.function": "Owner"}``; :data:`DROP` removes the key.
    :return: The changed copy.
    """
    payload = copy.deepcopy(payload)
    for path, value in changes.items():
        *parents, leaf = path.split(".")
        node = payload
        for parent in parents:
            node = node.setdefault(parent, {})
        if value is DROP:
            node.pop(leaf, None)
        else:
            node[leaf] = value
    return payload


OWNER: t.Final[dict[str, str]] = {
    "firstname": "Probe",
    "lastname": "Tester",
    "birthdate": "1980-01-01",
}

#: Case name -> (registration type of the baseline, changes against it).
CASES: t.Final[dict[str, tuple[str, dict[str, t.Any]]]] = {
    # Baselines
    "registered": ("registered", {}),
    "not_registered": ("not_registered", {}),
    "b2c (no companyInfo)": ("registered", {"companyInfo": DROP, "company": DROP}),
    # Mandatory fields, one at a time
    "registered -commercialRegisterNumber": ("registered", {"companyInfo.commercialRegisterNumber": DROP}),
    "registered -function": ("registered", {"companyInfo.function": DROP}),
    "registered -commercialSector": ("registered", {"companyInfo.commercialSector": DROP}),
    "registered -registrationType": ("registered", {"companyInfo.registrationType": DROP}),
    "registered -company": ("registered", {"company": DROP}),
    "registered -firstname -lastname": ("registered", {"firstname": DROP, "lastname": DROP}),
    "registered -birthDate": ("registered", {"birthDate": DROP}),
    "registered -email": ("registered", {"email": DROP}),
    "not_registered -function": ("not_registered", {"companyInfo.function": DROP}),
    "not_registered -commercialSector": ("not_registered", {"companyInfo.commercialSector": DROP}),
    "not_registered -company": ("not_registered", {"company": DROP}),
    "not_registered -birthDate": ("not_registered", {"birthDate": DROP}),
    "not_registered -email": ("not_registered", {"email": DROP}),
    "not_registered -firstname": ("not_registered", {"firstname": DROP}),
    "not_registered sole -birthDate": ("not_registered", {"companyInfo.companyType": "sole", "birthDate": DROP}),
    "not_registered SOLE -birthDate": ("not_registered", {"companyInfo.companyType": "SOLE", "birthDate": DROP}),
    "not_registered sole +owner -birthDate": (
        "not_registered", {"companyInfo.companyType": "sole", "companyInfo.owner": OWNER, "birthDate": DROP}),
    "registered -billingAddress": ("registered", {"billingAddress": DROP}),
    "registered billingAddress null": ("registered", {"billingAddress": None}),
    "registered billingAddress {}": ("registered", {"billingAddress": {}}),
    "registered billingAddress -street": ("registered", {"billingAddress.street": DROP}),
    "registered billingAddress street ''": ("registered", {"billingAddress.street": ""}),
    "registered billingAddress -name": ("registered", {"billingAddress.name": DROP}),
    "not_registered +commercialRegisterNumber": (
        "not_registered", {"companyInfo.commercialRegisterNumber": "HRB 12345"}),
    "companyInfo empty object": ("registered", {"companyInfo": {}}),
    "companyInfo null": ("registered", {"companyInfo": None}),
    # Values
    "registrationType REGISTERED": ("registered", {"companyInfo.registrationType": "REGISTERED"}),
    "registrationType nonsense": ("registered", {"companyInfo.registrationType": "nonsense"}),
    "function Owner": ("registered", {"companyInfo.function": "Owner"}),
    "function nonsense": ("registered", {"companyInfo.function": "nonsense"}),
    "function null": ("registered", {"companyInfo.function": None}),
    "commercialSector nonsense": ("registered", {"companyInfo.commercialSector": "nonsense"}),
    "commercialSector lowercase": ("registered", {"companyInfo.commercialSector": "other"}),
    "commercialSector WAREHOUSING..._ACTIVITIES_FOR_...": (
        "registered",
        {"companyInfo.commercialSector": "WAREHOUSING_AND_SUPPORT_ACTIVITIES_FOR_TRANSPORTATION"}),
    "commercialSector WAREHOUSING..._ACTIVITES_FOR_... (Java)": (
        "registered",
        {"companyInfo.commercialSector": "WAREHOUSING_AND_SUPPORT_ACTIVITES_FOR_TRANSPORTATION"}),
    "companyType company": ("registered", {"companyInfo.companyType": "company"}),
    "companyType sole": ("not_registered", {"companyInfo.companyType": "sole"}),
    "companyType COMPANY": ("registered", {"companyInfo.companyType": "COMPANY"}),
    "companyType nonsense": ("registered", {"companyInfo.companyType": "nonsense"}),
    # Owner
    "not_registered sole +owner": ("not_registered", {"companyInfo.companyType": "sole", "companyInfo.owner": OWNER}),
    "registered +owner": ("registered", {"companyInfo.owner": OWNER}),
    "owner birthdate dd.mm.yyyy": (
        "not_registered", {"companyInfo.owner": {**OWNER, "birthdate": "01.01.1980"}}),
    "owner birthdate nonsense": ("not_registered", {"companyInfo.owner": {**OWNER, "birthdate": "nonsense"}}),
    "owner birthDate (camelCase)": (
        "not_registered",
        {"companyInfo.owner": {"firstname": "Probe", "lastname": "Tester", "birthDate": "1980-01-01"}}),
    # Address.company
    "billingAddress.company": ("registered", {"billingAddress.company": "Probe GmbH Billing"}),
    "shippingAddress.company": ("registered", {"shippingAddress.company": "Probe GmbH Shipping"}),
    # Unknown key inside companyInfo
    "companyInfo unknown key": ("registered", {"companyInfo.nonsenseKey": "x"}),
}


def run_case(
        client: unzer.UnzerClient,
        name: str,
        *,
        execute: bool,
        dump: pathlib.Path | None,
) -> dict[str, t.Any]:
    """Send one case and read the customer back when it was accepted.

    :param client: The client to send with.
    :param name: Key into :data:`CASES`.
    :param execute: Perform the call; otherwise only print the payload.
    :param dump: Directory to write the returned customer to, if any.
    :return: What happened.
    """
    registration_type, changes = CASES[name]
    body = apply(base_payload(registration_type), changes)
    if not execute:
        print(f"DRY-RUN {name}: POST /v1/customers {json.dumps(body.get('companyInfo'))}")
        return {"case": name, "result": "dry-run"}

    try:
        created = client.request("customers", "POST", body)
    except unzer.model.ErrorResponse as err:
        return {
            "case": name,
            "result": "rejected",
            "codes": [e.code for e in err.errors],
            "messages": [e.merchantMessage for e in err.errors],
        }

    stored = client.request(f"customers/{created['id']}", "GET")
    if dump is not None:
        slug = "".join(c if c.isalnum() else "_" for c in name).strip("_")
        (dump / f"{slug}.json").write_text(json.dumps(stored, indent=2) + "\n")
    return {
        "case": name,
        "result": "accepted",
        "company": stored.get("company"),
        "companyInfo": stored.get("companyInfo", "<missing key>"),
        "billingAddress.company": stored.get("billingAddress", {}).get("company", "<missing key>"),
        "shippingAddress.company": stored.get("shippingAddress", {}).get("company", "<missing key>"),
    }


def main() -> None:
    """Run every case, or the selected ones, and print the results."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", action="append", choices=sorted(CASES),
                        help="run only these cases (default: all)")
    parser.add_argument("--execute", action="store_true",
                        help="actually call the sandbox (default: dry-run)")
    parser.add_argument("--dump", type=pathlib.Path,
                        help="write every returned customer as JSON into this directory")
    args = parser.parse_args()

    if not args.execute:
        print("DRY-RUN -- no requests are sent. Pass --execute to measure for real.\n")
    if args.dump is not None:
        args.dump.mkdir(parents=True, exist_ok=True)

    client = build_client()
    for name in args.case or CASES:
        result = run_case(client, name, execute=args.execute, dump=args.dump)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
