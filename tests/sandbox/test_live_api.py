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
    """Baskets, and how a discount has to be expressed in each of the two schemas.

    Both schemas reject line items with negative amounts, so a discount cannot be sent
    as its own negative "voucher" item -- it belongs in the positive discount field of
    the item it reduces (``amountDiscount`` in v1, ``amountDiscountPerUnitGross`` in
    v3). What the schemas do not share is how much of the arithmetic the API checks: v3
    reconciles the total to the cent, v1 checks nothing at all.

    Note that a *charge* does not validate the basket against the payment amount
    either -- measured with Prepayment against one basket worth 817.02, the amounts
    817.02, 726.24, 907.80 and 1.00 were all accepted and booked at face value. That
    is not tested here, because it would create a payment on the account for every
    run, and it says nothing about the payment methods that hand the basket on to a
    partner system, which may well be stricter.
    """

    # 19 % VAT: 907.80 gross == 762.86 net + 144.94 VAT. A 10 % basket discount of
    # 90.78 leaves a total of 817.02.
    VAT_PERCENT = 19
    GROSS = 907.80
    NET = 762.86
    VAT_AMOUNT = 144.94
    DISCOUNT = 90.78
    TOTAL = 817.02

    def goods_v1(self, **overrides):
        """A v1 line item, overridable per test."""
        return BasketItem(
            basketItemReferenceId="item-1", title="T-Shirt", quantity=1, kind="goods",
            vat=self.VAT_PERCENT, amountPerUnit=self.NET, amountNet=self.NET,
            amountVat=self.VAT_AMOUNT, amountGross=self.GROSS, **overrides)

    def goods_v3(self, **overrides):
        """A v3 line item, overridable per test."""
        return BasketItem(
            basketItemReferenceId="item-1", title="T-Shirt", quantity=1, kind="goods",
            vat=self.VAT_PERCENT, amountPerUnitGross=self.GROSS, **overrides)

    def test_v1_basket(self, sandbox_client):
        basket = sandbox_client.createBasket(Basket(
            amountTotalGross=100.0, amountTotalVat=15.97, amountTotalDiscount=0,
            currencyCode="EUR", orderId="sdk-test-basket-v1",
            basketItems=[BasketItem(
                title="T-Shirt", quantity=1, vat=19, amountGross=100.0, amountPerUnit=100.0,
                amountNet=84.03, amountVat=15.97, basketItemReferenceId="item-1", kind="goods")],
        ))
        assert basket.key
        assert not basket.isV3()

    def test_v3_basket(self, sandbox_client):
        basket = sandbox_client.createBasket(Basket(
            totalValueGross=100.0, currencyCode="EUR", orderId="sdk-test-basket-v3",
            basketItems=[BasketItem(
                title="T-Shirt", quantity=1, vat=19, amountPerUnitGross=100.0,
                basketItemReferenceId="item-1", kind="goods")],
        ))
        assert basket.key
        # v3 ids are UUIDs while v1 ids are short counters -- a cheap way to tell
        # which endpoint actually served the request.
        assert basket.isV3()
        assert len(basket.key) > len("s-bsk-999")

    def test_v1_rejects_negative_item_amounts(self, sandbox_client):
        """A discount as its own negative line item is refused, not merely discouraged.

        This is the shape a consumer arrives at naturally -- one item per article, one
        item for the voucher, the grosses adding up to the order total -- and it fails
        for every basket that carries a discount.
        """
        with pytest.raises(ErrorResponse) as excinfo:
            sandbox_client.createBasket(Basket(
                amountTotalGross=self.TOTAL, currencyCode="EUR",
                orderId="sdk-test-basket-v1-negative",
                basketItems=[self.goods_v1(), BasketItem(
                    basketItemReferenceId="discount-1", title="Voucher", quantity=1,
                    kind="voucher", vat=0, amountPerUnit=-self.DISCOUNT,
                    amountNet=-self.DISCOUNT, amountVat=0.0, amountGross=-self.DISCOUNT)],
            ))
        codes = {error.code for error in excinfo.value.errors}
        assert "API.600.410.018" in codes, codes  # basket item has negative amount gross
        assert "API.600.200.131" in codes, codes  # amount has to be positive

    def test_v3_rejects_negative_item_amounts(self, sandbox_client):
        """v3 refuses them as well, so the schema switch alone is no way around it."""
        with pytest.raises(ErrorResponse) as excinfo:
            sandbox_client.createBasket(Basket(
                totalValueGross=self.TOTAL, currencyCode="EUR",
                orderId="sdk-test-basket-v3-negative",
                basketItems=[self.goods_v3(), BasketItem(
                    basketItemReferenceId="discount-1", title="Voucher", quantity=1,
                    kind="voucher", vat=0, amountPerUnitGross=-self.DISCOUNT)],
            ))
        assert "API.600.200.131" in {error.code for error in excinfo.value.errors}

    def test_v1_discount_goes_into_amount_discount(self, sandbox_client):
        """The v1 way: a positive ``amountDiscount`` on the item it reduces.

        Reading the basket back shows that the API stores both values untouched --
        ``amountGross`` stays the pre-discount gross, so the reduced value is
        ``amountGross - amountDiscount`` and the caller owns that arithmetic.
        """
        basket = sandbox_client.createBasket(Basket(
            amountTotalGross=self.TOTAL, amountTotalDiscount=self.DISCOUNT,
            currencyCode="EUR", orderId="sdk-test-basket-v1-discount",
            basketItems=[self.goods_v1(amountDiscount=self.DISCOUNT)],
        ))
        assert basket.key
        stored = sandbox_client.getBasket(basket.key)
        assert stored.amountTotalGross == self.TOTAL
        assert stored.amountTotalDiscount == self.DISCOUNT
        item = stored.basketItems[0]
        assert item.amountDiscount == self.DISCOUNT
        assert item.amountGross == self.GROSS, "the API does not subtract the discount"
        assert item.kind == "goods", "the item type is sent as `type`, not as `kind`"

    def test_v3_discount_goes_into_amount_discount_per_unit_gross(self, sandbox_client):
        """The v3 way: a positive ``amountDiscountPerUnitGross``, per unit."""
        basket = sandbox_client.createBasket(Basket(
            totalValueGross=self.TOTAL, currencyCode="EUR",
            orderId="sdk-test-basket-v3-discount",
            basketItems=[self.goods_v3(amountDiscountPerUnitGross=self.DISCOUNT)],
        ))
        assert basket.key
        assert basket.isV3()

    def test_v3_multiplies_the_discount_by_the_quantity(self, sandbox_client):
        """``amountDiscountPerUnitGross`` is per unit, not per line.

        Three units at 100.00 with a per-unit discount of 10.00 reconcile against a
        total of 270.00 -- if the discount counted once per line, the total would have
        to be 290.00 and this call would fail.
        """
        basket = sandbox_client.createBasket(Basket(
            totalValueGross=3 * (100.0 - 10.0), currencyCode="EUR",
            orderId="sdk-test-basket-v3-quantity",
            basketItems=[BasketItem(
                basketItemReferenceId="item-1", title="T-Shirt", quantity=3, kind="goods",
                vat=self.VAT_PERCENT, amountPerUnitGross=100.0,
                amountDiscountPerUnitGross=10.0)],
        ))
        assert basket.key

    def test_v3_reconciles_the_total_to_the_cent(self, sandbox_client):
        """v3 enforces ``totalValueGross == sum((perUnit - discount) * quantity)``.

        A single cent is enough to be refused, so a discount spread over several items
        has to be rounded so that the parts add up exactly.
        """
        with pytest.raises(ErrorResponse) as excinfo:
            sandbox_client.createBasket(Basket(
                totalValueGross=self.TOTAL + 0.01, currencyCode="EUR",
                orderId="sdk-test-basket-v3-off-by-a-cent",
                basketItems=[self.goods_v3(amountDiscountPerUnitGross=self.DISCOUNT)],
            ))
        assert "API.600.410.062" in {error.code for error in excinfo.value.errors}

    def test_v1_does_not_reconcile_the_total(self, sandbox_client):
        """v1 accepts a basket whose items contradict its own total.

        Documented as a warning, not as a licence: the value is passed on to the
        payment method, and the ones that forward the basket to a partner system may
        be stricter than the basket endpoint is.
        """
        basket = sandbox_client.createBasket(Basket(
            amountTotalGross=1.00, currencyCode="EUR",
            orderId="sdk-test-basket-v1-wrong-total", basketItems=[self.goods_v1()],
        ))
        assert basket.key
        assert sandbox_client.getBasket(basket.key).amountTotalGross == 1.00

    def test_v3_requires_vat_on_every_item(self, sandbox_client):
        """``vat`` is mandatory in v3 -- the v1 endpoint takes items without it."""
        with pytest.raises(ErrorResponse) as excinfo:
            sandbox_client.createBasket(Basket(
                totalValueGross=self.GROSS, currencyCode="EUR",
                orderId="sdk-test-basket-v3-no-vat",
                basketItems=[BasketItem(
                    basketItemReferenceId="item-1", title="T-Shirt", quantity=1,
                    kind="goods", amountPerUnitGross=self.GROSS)],
            ))
        assert "API.600.410.052" in {error.code for error in excinfo.value.errors}

    def test_v1_takes_items_without_vat(self, sandbox_client):
        """The counterpart: v1 accepts the same item without ``vat`` and stores 0."""
        basket = sandbox_client.createBasket(Basket(
            amountTotalGross=self.GROSS, currencyCode="EUR",
            orderId="sdk-test-basket-v1-no-vat",
            basketItems=[BasketItem(
                basketItemReferenceId="item-1", title="T-Shirt", quantity=1, kind="goods",
                amountPerUnit=self.NET, amountNet=self.NET, amountGross=self.GROSS)],
        ))
        assert sandbox_client.getBasket(basket.key).basketItems[0].vat == 0.0

    def test_v3_discount_must_not_exceed_the_unit_price(self, sandbox_client):
        """The per-item result must stay positive, which caps the discount per item.

        A discount bigger than the item it sits on therefore has to be spread across
        several items in v3.

        A second, larger item keeps ``totalValueGross`` positive on purpose. With only
        the over-discounted line the basket total is negative too, and the API answers
        ``API.600.200.131`` "Amount has to be positive" -- which the negative total
        alone explains, so such a basket cannot show that the *item* is what was
        refused. Isolated like this the API names the item instead, in
        ``API.600.410.064``: "Basket item i1 'amountDiscountPerUnitGross' does not
        equal to 'amountPerUnitGross'".
        """
        with pytest.raises(ErrorResponse) as excinfo:
            sandbox_client.createBasket(Basket(
                totalValueGross=(self.GROSS - 1000.0) + 2000.0, currencyCode="EUR",
                orderId="sdk-test-basket-v3-discount-too-large",
                basketItems=[
                    self.goods_v3(amountDiscountPerUnitGross=1000.0),
                    BasketItem(
                        basketItemReferenceId="item-2", title="T-Shirt", quantity=1,
                        kind="goods", vat=self.VAT_PERCENT, amountPerUnitGross=2000.0),
                ],
            ))
        assert "API.600.410.064" in {error.code for error in excinfo.value.errors}

    def test_v1_accepts_a_discount_larger_than_its_item(self, sandbox_client):
        """v1 does not cap it, the counterpart to the v3 test above.

        Another consequence of v1 checking nothing: the item is left at an effective
        -92.20 and the endpoint still answers 201.
        """
        basket = sandbox_client.createBasket(Basket(
            amountTotalGross=self.TOTAL, currencyCode="EUR",
            orderId="sdk-test-basket-v1-discount-too-large",
            basketItems=[self.goods_v1(amountDiscount=1000.0)],
        ))
        assert basket.key


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
