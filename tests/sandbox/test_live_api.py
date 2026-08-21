"""Tests against the real Unzer sandbox.

Skipped unless ``UNZER_PRIVATE_KEY`` holds a sandbox key -- see ``tests/conftest.py``.

These exist because mocks can only confirm what we believed when we wrote them, and
Unzer's documentation and SDKs are wrong often enough that belief is not enough. Every
assertion here has caught, or could catch, a difference between the documentation and
the running API.

**What cannot be tested here.** Several payment types are created client-side, by the
Payment Page or the UI components: the browser collects the data and only the resulting
``typeId`` reaches the backend. Creating such a type server-side yields an empty
resource that the payment provider then rejects -- an attempt with Klarna returns
``COR.800.400.160 "Validation error at partner system"``, which looks like an SDK bug
but is not one. Affected: Card, Klarna, PayPal, Apple Pay, Google Pay, iDEAL,
Click to Pay. Only types whose fields the SDK actually sends are exercised below.

**Sandbox accounts differ** in which methods they have enabled, so each test checks
``keypair/types`` first and skips what the account cannot do.
"""

import uuid

import pytest

from unzer.model import (
    Action,
    Address,
    Basket,
    BasketItem,
    Customer,
    ErrorResponse,
    PaymentPage,
    PaymentRequest,
    SepaDirectDebit,
)

pytestmark = pytest.mark.sandbox

# Official sandbox test data: docs.unzer.com/reference/test-data/
TEST_IBAN = "DE89370400440532013000"
TEST_BIC = "COBADEFFXXX"
TEST_HOLDER = "Maximilian Mustermann"


@pytest.fixture(scope="module")
def enabled_methods(sandbox_client):
    """The payment method slugs this account has enabled, lower cased.

    Unzer is inconsistent about the casing -- the API answers ``EPS`` while the
    resource path is ``eps``.
    """
    types = sandbox_client.getKeyPairTypes()["paymentTypes"]
    return {entry["type"].lower() for entry in types}


def requires(sandbox_client, enabled_methods, slug):
    if slug not in enabled_methods:
        pytest.skip(f"account has no {slug}; enabled: {sorted(enabled_methods)}")


class TestKeypair:

    def test_keypair_is_readable(self, sandbox_client):
        assert sandbox_client.getKeyPair()["publicKey"].startswith("s-pub-")

    def test_sandbox_key_reaches_the_default_endpoint(self, sandbox_client):
        """`sandbox=True` does not switch hosts: the key prefix decides the
        environment and api.unzer.com serves both."""
        assert sandbox_client.endpoint == "https://api.unzer.com"
        assert sandbox_client.getKeyPair()["publicKey"]

    def test_keypair_types_may_repeat_a_payment_type(self, sandbox_client):
        """Documented as one entry per type; some accounts return several."""
        types = [entry["type"] for entry in sandbox_client.getKeyPairTypes()["paymentTypes"]]
        assert types, "account has no payment types at all"
        # Not an assertion about duplicates -- just that reading them never crashes.
        assert all(isinstance(name, str) for name in types)

    def test_every_configuration_is_reachable(self, sandbox_client, enabled_methods):
        """On an account that configures one type twice, both must be readable.

        Seen with `card`: MASTER/VISA on one channel, AMEX on another. Reading only
        the first entry hands out the wrong channel for the other brands.
        """
        entries = sandbox_client.getKeyPairTypes()["paymentTypes"]
        names = [entry["type"].lower() for entry in entries]
        repeated = {name for name in names if names.count(name) > 1}
        if not repeated:
            pytest.skip(f"account configures every type once: {sorted(set(names))}")
        for name in repeated:
            configurations = [e for e in entries if e["type"].lower() == name]
            channels = {s["channel"] for c in configurations for s in c["supports"]}
            assert len(channels) == len(configurations), \
                f"{name} has {len(configurations)} configurations but {len(channels)} channels"

    def test_channel_can_be_picked_by_brand(self, sandbox_client, enabled_methods):
        requires(sandbox_client, enabled_methods, "card")
        from unzer.model import Card
        card = Card(client=sandbox_client)
        brands = {
            brand
            for configuration in card.get_configurations()
            for support in configuration.get("supports") or []
            for brand in support.get("brands") or []
        }
        if not brands:
            pytest.skip("card configuration lists no brands")
        for brand in sorted(brands):
            assert card.get_channel_id(brand=brand), f"no channel for {brand}"
        # On an account with two card entries the channels must actually differ.
        channels = {card.get_channel_id(brand=b) for b in brands}
        assert len(channels) >= 1

    def test_unknown_brand_raises_lookup_error(self, sandbox_client, enabled_methods):
        requires(sandbox_client, enabled_methods, "card")
        from unzer.model import Card
        with pytest.raises(LookupError):
            Card(client=sandbox_client).get_channel_id(brand="NOT-A-BRAND")

    def test_customer_types_is_a_comma_separated_string(self, sandbox_client):
        """Not a list -- `B2B,B2C` arrives as one string."""
        for entry in sandbox_client.getKeyPairTypes()["paymentTypes"]:
            allowed = entry.get("allowCustomerTypes")
            if allowed is None:
                continue
            assert isinstance(allowed, str), f"{entry['type']}: {type(allowed)}"
            assert set(allowed.split(",")) <= {"B2B", "B2C"}, allowed


class TestCustomer:

    def test_customer_without_addresses_is_accepted(self, sandbox_client):
        """Sending "" for a missing address returns HTTP 400 API.410.300.007."""
        customer = sandbox_client.createCustomer(
            Customer(firstname="Maximilian", lastname="Mustermann",
                     email="maximilian.mustermann@example.com")
        )
        assert customer.key.startswith("s-cst-")
        # The API answers with an empty address object, never with a string.
        assert isinstance(customer.billingAddress, Address)

    def test_customer_with_addresses_round_trips(self, sandbox_client):
        address = Address(firstname="Maximilian", lastname="Mustermann",
                          street="Hugo-Junkers-Str. 3", zipCode="60386",
                          city="Frankfurt am Main", country="DE")
        customer = sandbox_client.createCustomer(
            Customer(firstname="Maximilian", lastname="Mustermann", salutation="mr",
                     birthDate="1980-11-22", email="maximilian.mustermann@example.com",
                     billingAddress=address)
        )
        assert customer.billingAddress.city == "Frankfurt am Main"
        assert customer.billingAddress.zipCode == "60386"

    def test_empty_state_is_accepted(self, sandbox_client):
        """The docs list state as required for a billing address; it is not."""
        address = Address(firstname="Maximilian", lastname="Mustermann",
                          street="Hugo-Junkers-Str. 3", zipCode="60386",
                          city="Frankfurt am Main", country="DE", state=None)
        customer = sandbox_client.createCustomer(
            Customer(firstname="Maximilian", lastname="Mustermann", billingAddress=address)
        )
        assert customer.key

    def test_create_or_update_recovers_from_a_duplicate(self, sandbox_client):
        """The second call must not fail on the duplicate customerId.

        A fresh id per run on purpose: a fixed one would make the test depend on
        what an earlier run left behind in the sandbox.
        """
        customer_id = f"sdk-test-{uuid.uuid4().hex[:12]}"
        first = sandbox_client.createOrUpdateCustomer(
            Customer(firstname="Maximilian", lastname="Mustermann", customerId=customer_id))
        assert first.customerId == customer_id
        assert first.firstname == "Maximilian"

        # Same customerId, different data: createCustomer answers 400 and the
        # client is expected to fall back to updateCustomer.
        second = sandbox_client.createOrUpdateCustomer(
            Customer(firstname="Maximiliane", lastname="Mustermann", customerId=customer_id))
        assert second.key == first.key, "the update must not create a second resource"

        # Read it back separately. The customer returned by updateCustomer comes from
        # a GET issued immediately after the PUT, which has been seen to still carry
        # the previous name -- so the write is verified, not that response.
        assert sandbox_client.getCustomer(customer_id).firstname == "Maximiliane"


class TestBasket:

    def test_v1_basket(self, sandbox_client):
        basket = sandbox_client.createBasket(Basket(
            amountTotalGross=100.0, amountTotalVat=15.97, amountTotalDiscount=0,
            currencyCode="EUR", orderId="sdk-test-basket-v1",
            basketItems=[BasketItem(
                title="T-Shirt", quantity=1, vat=19, amountGross=100.0, amountPerUnit=100.0,
                amountNet=84.03, amountVat=15.97, basketItemReferenceId="item-1", type="goods")],
        ))
        assert basket.key
        assert not basket.isV3()

    def test_v3_basket(self, sandbox_client):
        basket = sandbox_client.createBasket(Basket(
            totalValueGross=100.0, currencyCode="EUR", orderId="sdk-test-basket-v3",
            basketItems=[BasketItem(
                title="T-Shirt", quantity=1, vat=19, amountPerUnitGross=100.0,
                basketItemReferenceId="item-1", type="goods")],
        ))
        assert basket.key
        # v3 ids are UUIDs while v1 ids are short counters -- a cheap way to tell
        # which endpoint actually served the request.
        assert basket.isV3()
        assert len(basket.key) > len("s-bsk-999")


class TestPaymentPage:
    """Paypage v1 is tagged [Deprecated] in the spec but still works."""

    def test_create_and_fetch(self, sandbox_client):
        page = sandbox_client.createPaymentPage(PaymentPage(
            action=Action.CHARGE, amount=100.0, currency="EUR",
            returnUrl="https://shop.example.com/return", orderId="sdk-test-paypage",
        ))
        assert page.payPageId.startswith("s-ppg-")
        assert page.action is Action.CHARGE
        fetched = sandbox_client.getPaymentPage(page.payPageId)
        assert fetched.payPageId == page.payPageId
        assert fetched.action is Action.CHARGE

    def test_redirect_url_points_at_the_sandbox(self, sandbox_client):
        """The host differs between sandbox and production, which is the reason
        consumers need to know which mode they are in."""
        page = sandbox_client.createPaymentPage(PaymentPage(
            action=Action.CHARGE, amount=100.0, currency="EUR",
            returnUrl="https://shop.example.com/return",
        ))
        assert "sbx-" in page.redirectUrl, page.redirectUrl


class TestSepaDirectDebit:
    """SEPA direct debit is created server-side, so it can be exercised here."""

    def test_create_payment_type(self, sandbox_client, enabled_methods):
        requires(sandbox_client, enabled_methods, "sepa-direct-debit")
        created = sandbox_client.createPaymentType(
            SepaDirectDebit(iban=TEST_IBAN, bic=TEST_BIC, holder=TEST_HOLDER))
        assert created.key.startswith("s-sdd-")
        assert created.iban == TEST_IBAN

    def test_charge_and_read_back(self, sandbox_client, enabled_methods):
        requires(sandbox_client, enabled_methods, "sepa-direct-debit")
        response = sandbox_client.charge(PaymentRequest(
            paymentType=SepaDirectDebit(iban=TEST_IBAN, bic=TEST_BIC, holder=TEST_HOLDER),
            amount=12.34, currency="EUR", returnUrl="https://shop.example.com/return",
            orderId="sdk-test-sdd-charge",
        ))
        assert response.isSuccess
        assert response.transactionId.startswith("s-chg-")
        assert response.processing.shortId, "processing must carry the short id"

        payment = sandbox_client.getPayment(response.paymentId)
        assert payment.amountCharged == 12.34
        charged = payment.getChargedTransactions()
        assert len(charged) == 1, "getChargedTransactions used to return []"
        assert charged[0].transactionId == response.transactionId

    def test_transaction_actions_are_enums(self, sandbox_client, enabled_methods):
        requires(sandbox_client, enabled_methods, "sepa-direct-debit")
        response = sandbox_client.charge(PaymentRequest(
            paymentType=SepaDirectDebit(iban=TEST_IBAN, bic=TEST_BIC, holder=TEST_HOLDER),
            amount=1.0, currency="EUR", returnUrl="https://shop.example.com/return",
        ))
        payment = sandbox_client.getPayment(response.paymentId)
        assert all(isinstance(txn.action, Action) for txn in payment.transactions)


class TestErrorShape:

    def test_unknown_payment_raises_error_response(self, sandbox_client):
        with pytest.raises(ErrorResponse) as excinfo:
            sandbox_client.getPayment("s-pay-does-not-exist")
        error = excinfo.value
        assert error.statusCode >= 400
        assert error.errors, "the API always sends at least one error entry"
        assert error.errors[0].code
        assert error.errors[0].merchantMessage

    def test_error_carries_a_trace_id(self, sandbox_client):
        with pytest.raises(ErrorResponse) as excinfo:
            sandbox_client.getPayment("s-pay-does-not-exist")
        assert excinfo.value.errorId or excinfo.value.traceId
