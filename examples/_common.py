"""Shared setup for the examples: credentials from the environment, sandbox only."""

import logging
import os
import sys

import unzer


def build_client(verbose: bool = False) -> unzer.UnzerClient:
    """Create a client from ``UNZER_PRIVATE_KEY`` / ``UNZER_PUBLIC_KEY``.

    :param verbose: Log the full requests and responses. Note that this includes
        IBANs and customer names -- fine for a sandbox, not for production.
    :return: A client bound to the sandbox.
    """
    private_key = os.environ.get("UNZER_PRIVATE_KEY")
    public_key = os.environ.get("UNZER_PUBLIC_KEY", "")
    if not private_key:
        sys.exit("UNZER_PRIVATE_KEY is not set. See examples/README.md.")
    if not private_key.startswith("s-priv-"):
        sys.exit(
            "Refusing to run: UNZER_PRIVATE_KEY is not a sandbox key. Sandbox keys "
            "start with 's-priv-'. These examples create real transactions."
        )
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.getLogger("unzer-sdk").setLevel(logging.DEBUG)
    return unzer.UnzerClient(private_key, public_key, sandbox=True)


def require_method(client: unzer.UnzerClient, slug: str) -> None:
    """Exit with a readable message if the account has no such payment method.

    Sandbox accounts differ in what is enabled, and the API's error for a missing
    method is not obvious.
    """
    # Compared case-insensitively: the API answers "EPS" while the path is "eps".
    enabled = {
        entry["type"].lower()
        for entry in client.getKeyPairTypes()["paymentTypes"]
    }
    if slug.lower() not in enabled:
        sys.exit(
            f"This account has no '{slug}'. Enabled: {', '.join(sorted(enabled))}"
        )
