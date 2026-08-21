"""One test per fixed bug.

Every test in here fails on the code as it was before the fix, and the docstring
names what went wrong. Verified against the sandbox where the API was involved --
see AGENTS.md on why the API, and not the documentation, is the reference.
"""

import pytest
import requests
import responses

from unzer.model import (
    Action,
    Address,
    Customer,
    Events,
    PaymentGetResponse,
    PaymentPage,
    PaymentPageResponse,
    PaymentRequest,
    PaymentType,
    PaymentTypes,
    TransactionStatus,
    Webhook,
)

BASE = "https://api.unzer.com/v1"


class TestPaymentPageWasUnusable:
    """The enum migration in 9fdc60c broke all three paypage paths."""

    def test_action_enum_is_not_interpolated_into_the_url(self, client, fixture_json):
        """Was "paypage/Action.CHARGE" -> HTTP 405 API.000.000.006 from the API."""
        responses.start()
        try:
            responses.add(responses.POST, f"{BASE}/paypage/charge", json=fixture_json("paypage"))
            page = PaymentPage(action=Action.CHARGE, amount=100.0,
                               returnUrl="https://shop.example.com/return")
            client.createPaymentPage(page)
            assert responses.calls[0].request.url == f"{BASE}/paypage/charge"
        finally:
            responses.stop()
            responses.reset()

    def test_response_with_upper_case_action_parses(self, fixture_json):
        """The API answers action="CHARGE"; the constructor only took enum members."""
        assert fixture_json("paypage")["action"] == "CHARGE"
        page = PaymentPageResponse.fromDict(fixture_json("paypage"))
        assert page.action is Action.CHARGE

    def test_card3ds_may_be_omitted(self):
        """Default None hit `not isinstance(card3ds, bool)` -- every plain call raised."""
        page = PaymentPage(action=Action.CHARGE, amount=100.0, returnUrl="https://e.com/r")
        assert page.card3ds is None

    def test_card3ds_still_rejects_nonsense(self):
        with pytest.raises(TypeError):
            PaymentPage(action=Action.CHARGE, amount=1.0, returnUrl="https://e.com/r",
                        card3ds="yes")


class TestChargedTransactionsWereAlwaysEmpty:

    def test_transaction_action_is_an_enum(self, fixture_json, client):
        """fromDict stored the lowercase string, so `txn.action == Action.CHARGE`
        was always False and getChargedTransactions() returned []."""
        payment = PaymentGetResponse.fromDict(fixture_json("payment_get"), client)
        charge = [t for t in payment.transactions if t.action is Action.CHARGE]
        assert len(charge) == 1
        assert charge[0].status is TransactionStatus.SUCCESS

    @responses.activate
    def test_get_charged_transactions_finds_the_charge(self, fixture_json, client):
        responses.add(responses.GET, f"{BASE}/payments/s-pay-123456/charges/s-chg-1",
                      json=fixture_json("charge"))
        payment = PaymentGetResponse.fromDict(fixture_json("payment_get"), client)
        assert len(payment.getChargedTransactions()) == 1


class TestCustomerWithoutAddresses:

    def test_missing_addresses_serialise_to_none(self):
        """Sending "" made the API answer HTTP 400 API.410.300.007 ("HTTP message
        not readable"), because the field is an object. null is accepted."""
        data = Customer(firstname="A", lastname="B").serialize()
        assert data["billingAddress"] is None
        assert data["shippingAddress"] is None

    def test_present_addresses_still_serialise_to_objects(self):
        customer = Customer(firstname="A", lastname="B",
                            billingAddress=Address(firstname="A", lastname="B", city="Berlin"))
        assert customer.serialize()["billingAddress"]["city"] == "Berlin"

    def test_wrong_address_type_raises_instead_of_asserting(self):
        """Was a bare `assert`, which vanishes under `python -O`."""
        customer = Customer(firstname="A", lastname="B", billingAddress="Hauptstr. 1")
        with pytest.raises(TypeError, match="billingAddress"):
            customer.serialize()


class TestWebhookEvents:

    @pytest.mark.parametrize("member,expected", [
        (Events.AUTHORIZE_PENDING, "authorize.pending"),
        (Events.CHARGE_PENDING, "charge.pending"),
    ])
    def test_pending_events_are_spelled_correctly(self, member, expected):
        """Were "authorize.pendin" and "charge.pendin" -- registered but never fired."""
        assert member == expected

    @pytest.mark.parametrize("name", [
        "preauthorize", "preauthorize.succeeded", "preauthorize.failed",
        "preauthorize.pending", "preauthorize.canceled", "preauthorize.expired",
        "authorize.resumed", "charge.resumed",
    ])
    def test_events_missing_before_are_available(self, name):
        assert Events(name).value == name

    def test_setter_no_longer_accepts_class_internals(self):
        """Validation went against vars(Events).values(), which also contains
        __module__ and __qualname__, so those strings passed as valid events."""
        with pytest.raises(TypeError):
            Webhook(url="https://e.com/h", event="unzer.model.webhook")


class TestWebhookListsWereIterators:

    @responses.activate
    def test_list_webhooks_can_be_used_twice(self, client, fixture_json):
        """Returned a map object: len() failed and a second pass was empty."""
        responses.add(responses.GET, f"{BASE}/webhooks", json=fixture_json("webhooks_list"))
        hooks = client.listWebhooks()
        assert len(hooks) == 2
        assert len(list(hooks)) == 2, "the result was consumed by the first pass"


class TestUnknownPaymentTypePlaceholder:

    def test_placeholder_raises_a_readable_error(self):
        """method_name used to be the plain string "N/A", so the client crashed
        with AttributeError: 'str' object has no attribute 'value'."""
        cls = PaymentType.construct(PaymentTypes.GIROPAY)
        with pytest.raises(NotImplementedError, match="no implementation"):
            cls.method_name.value

    def test_placeholder_class_has_a_usable_name(self):
        """Was "Paymenttypes.Giropay"."""
        assert PaymentType.construct(PaymentTypes.GIROPAY).__name__ == "GiropayPaymentType"


class TestRetryOnNonIdempotentMethods:
    """Issue #7: a retried POST can repeat a payment operation."""

    @responses.activate
    def test_post_is_not_repeated_after_a_timeout(self, retrying_client):
        responses.add(responses.POST, f"{BASE}/customers", body=requests.exceptions.ReadTimeout())
        with pytest.raises(requests.exceptions.ReadTimeout):
            retrying_client.createCustomer(Customer(firstname="A", lastname="B"))
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_is_still_repeated(self, retrying_client, fixture_json):
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1",
                      body=requests.exceptions.ReadTimeout())
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1", json=fixture_json("payment_get"))
        retrying_client.getPayment("s-pay-1")
        assert len(responses.calls) == 2


class TestTransactionUrlParsing:

    @pytest.mark.parametrize("url,expected", [
        (f"{BASE}/payments/s-pay-1/charges/s-chg-1/cancels/s-cnl-1", "cancels"),
        # Hyphenated sub-operations were silently dropped by [a-z]+
        (f"{BASE}/payments/s-pay-1/charges/s-chg-1/chargeback-reversal/s-cbr-1",
         "chargeback-reversal"),
        (f"{BASE}/payments/s-pay-1/charges/s-chg-1/due-date-extensions/s-dde-1",
         "due-date-extensions"),
    ])
    def test_hyphenated_sub_operations_are_kept(self, url, expected):
        from unzer.model.payment import paymentUrlRe
        assert paymentUrlRe.match(url).groupdict()["subSubOperation"] == expected

    @pytest.mark.parametrize("host", ["api.unzer.com", "sbx-api.unzer.com"])
    def test_host_is_not_pinned(self, host):
        """The pattern was anchored to api.unzer.com/v1 and failed on any other host."""
        from unzer.model.payment import paymentUrlRe
        url = f"https://{host}/v1/payments/s-pay-1/charges/s-chg-1"
        assert paymentUrlRe.match(url) is not None

    def test_missing_url_raises_a_value_error(self, client):
        """Was a bare `assert`, so it disappeared under `python -O`."""
        from unzer.model.payment import PaymentTransaction
        with pytest.raises(ValueError, match="no url"):
            PaymentTransaction.fromDict({"url": "", "status": "success", "type": "charge",
                                         "date": "2026-08-21 10:15:32", "amount": "1.0"})


class TestTypeIdParsing:

    @pytest.mark.parametrize("type_id", ["nonsense", "s-crd", "x"])
    def test_malformed_type_id_raises_value_error(self, type_id):
        """"nonsense".split("-")[1] raised IndexError instead of a readable error."""
        with pytest.raises(ValueError, match="Invalid typeId"):
            PaymentGetResponse.getPaymentTypeFromTypeId(type_id)

    @pytest.mark.parametrize("type_id", ["", None])
    def test_empty_type_id_raises(self, type_id):
        with pytest.raises(ValueError, match="Invalid typeId"):
            PaymentGetResponse.getPaymentTypeFromTypeId(type_id)

    def test_unknown_short_code_says_what_to_do(self):
        """No placeholder return value: the message names the fix instead."""
        with pytest.raises(ValueError, match="has to be added to PaymentTypes"):
            PaymentGetResponse.getPaymentTypeFromTypeId("s-xyz-abc123")

    @pytest.mark.parametrize("type_id,expected", [
        ("s-crd-abc123", "CARD"),
        ("p-sdd-abc123", "SEPA_DIRECT_DEBIT"),
        ("s-pit-abc123", "PAYLATER_INSTALLMENT"),
        ("s-obp-abc123", "OPEN_BANKING"),
    ])
    def test_known_short_codes(self, type_id, expected):
        assert PaymentGetResponse.getPaymentTypeFromTypeId(type_id).name == expected


class TestKeypairWithSeveralConfigurations:

    @responses.activate
    def test_all_configurations_are_returned(self, client):
        """A keypair can hold the same payment type more than once -- observed with
        card, twice, with different brands. get_configuration() silently returned
        whichever came first."""
        responses.add(responses.GET, f"{BASE}/keypair/types", json={"paymentTypes": [
            {"type": "card", "supports": [{"channel": "chan-a", "brands": ["VISA"]}]},
            {"type": "card", "supports": [{"channel": "chan-b", "brands": ["MASTER"]}]},
        ]})
        from unzer.model import Card
        assert len(Card(client=client).get_configurations()) == 2

    @responses.activate
    def test_casing_is_ignored(self, client):
        """The API answers "EPS" while the resource path is "eps"."""
        responses.add(responses.GET, f"{BASE}/keypair/types", json={"paymentTypes": [
            {"type": "EPS", "supports": [{"channel": "chan", "brands": []}]},
        ]})
        from unzer.model import Eps
        assert Eps(client=client).get_configuration()["type"] == "EPS"

    @responses.activate
    def test_unconfigured_type_raises_lookup_error(self, client):
        responses.add(responses.GET, f"{BASE}/keypair/types", json={"paymentTypes": []})
        from unzer.model import Card
        with pytest.raises(LookupError):
            Card(client=client).get_configurations()


class TestChannelPerBrand:
    """A real keypair holds two card entries: MASTER/VISA and AMEX, on different
    channels. get_channel_id() returned whichever came first, so callers got the
    wrong channel for every brand but the first."""

    @pytest.fixture
    def keypair(self, fixture_json):
        responses.add(responses.GET, f"{BASE}/keypair/types",
                      json=fixture_json("keypair_types_multi_card"))

    @responses.activate
    def test_channel_is_selected_by_brand(self, client, keypair):
        from unzer.model import Card
        card = Card(client=client)
        assert card.get_channel_id(brand="VISA") == "a" * 32
        assert card.get_channel_id(brand="AMEX") == "b" * 32

    @responses.activate
    def test_brand_matching_ignores_casing(self, client, keypair):
        from unzer.model import Card
        assert Card(client=client).get_channel_id(brand="amex") == "b" * 32

    @responses.activate
    def test_brands_are_scoped_to_the_selected_configuration(self, client, keypair):
        from unzer.model import Card
        assert Card(client=client).get_brands(brand="AMEX") == ["AMEX"]

    @responses.activate
    def test_unknown_brand_names_the_available_ones(self, client, keypair):
        from unzer.model import Card
        with pytest.raises(LookupError, match="AMEX"):
            Card(client=client).get_channel_id(brand="DINERS")

    @responses.activate
    def test_without_brand_the_first_entry_still_wins(self, client, keypair):
        """Kept for backwards compatibility -- but it now logs a warning."""
        from unzer.model import Card
        assert Card(client=client).get_channel_id() == "a" * 32

    @responses.activate
    def test_single_configuration_needs_no_brand(self, client, keypair):
        from unzer.model import Eps
        assert Eps(client=client).get_channel_id() == "c" * 32


class TestTransactionTypesBeyondAuthorizeAndCharge:
    """A payment lists every transaction it has, not only the two this SDK creates.

    Converting `type` to the Action enum initially only knew charge and authorize,
    so getPayment() raised ValueError for any payment that had been cancelled,
    shipped or paid out -- worse than the silent bug it replaced.

    Which makes completeness the fix, not tolerance: all eight types the API knows
    are declared, so a payment reads back whatever happened to it.
    """

    @pytest.mark.parametrize("wire,expected", [
        ("authorize", Action.AUTHORIZE),
        ("preauthorize", Action.PREAUTHORIZE),
        ("charge", Action.CHARGE),
        ("cancel-authorize", Action.REVERSAL),
        ("cancel-charge", Action.REFUND),
        ("shipment", Action.SHIPMENT),
        ("payout", Action.PAYOUT),
        ("chargeback", Action.CHARGEBACK),
        ("strong_customer_authentication", Action.SCA),
    ])
    def test_every_transaction_type_of_the_php_sdk_is_known(self, wire, expected):
        transaction = self._transaction(wire)
        assert transaction.action is expected

    @pytest.mark.parametrize("wire,expected", [
        ("success", TransactionStatus.SUCCESS),
        ("pending", TransactionStatus.PENDING),
        ("error", TransactionStatus.ERROR),
        ("resumed", TransactionStatus.RESUMED),
    ])
    def test_every_transaction_status_is_known(self, wire, expected):
        from unzer.model.payment import PaymentTransaction
        transaction = PaymentTransaction.fromDict({
            "type": "charge", "status": wire, "date": "2026-08-21 10:15:32",
            "amount": "1.0000", "participantId": "",
            "url": "https://api.unzer.com/v1/payments/s-pay-1/charges/s-chg-1",
        })
        assert transaction.status is expected

    @pytest.mark.parametrize("code", [0, 1, 2, 3, 4, 5, 6])
    def test_known_payment_states(self, code):
        from unzer.model import PaymentState
        assert PaymentState(code).value == code

    def test_unknown_payment_state_raises(self, fixture_json, client):
        """No fallback here, on purpose. There are seven states and they have been
        stable for years; an eighth is news, and swallowing it into UNKNOWN would
        surface later as "not COMPLETED, so not paid" without saying why."""
        from unzer.model import PaymentGetResponse
        data = fixture_json("payment_get")
        data["state"] = {"id": 99, "name": "something-new"}
        with pytest.raises(ValueError, match="99"):
            PaymentGetResponse.fromDict(data, client)

    @staticmethod
    def _transaction(wire_type):
        from unzer.model.payment import PaymentTransaction
        return PaymentTransaction.fromDict({
            "type": wire_type, "status": "success", "date": "2026-08-21 10:15:32",
            "amount": "50.0000", "participantId": "",
            "url": "https://api.unzer.com/v1/payments/s-pay-1/charges/s-chg-1/cancels/s-cnl-1",
        })


class TestUnknownEnumValuesRaise:
    """An unknown enum value is a defect, not something to paper over.

    A placeholder member would also be indistinguishable from a real one: the API
    genuinely answers `salutation: "unknown"`, where it means "not known about this
    customer" rather than "this SDK is behind". Letting ValueError through names the
    offending value and points at the parsing code.
    """

    @pytest.mark.parametrize("value", ["cancel-everything", "chrage", ""])
    def test_unknown_action_raises(self, value):
        with pytest.raises(ValueError):
            Action(value)

    def test_action_covers_every_type_the_source_declares(self):
        """Nine, not eight: TransactionTypes.php also has SCA. A missing member
        makes getPayment() raise for the whole payment, so this list has to stay
        complete — there is no fallback to absorb an omission."""
        assert {a.value for a in Action} == {
            "authorize", "preauthorize", "charge", "cancel-authorize",
            "cancel-charge", "shipment", "payout", "chargeback",
            "strong_customer_authentication",
        }

    def test_unknown_transaction_type_in_a_response_raises(self):
        with pytest.raises(ValueError, match="brandnew"):
            self._transaction("brandnew")

    def test_unknown_transaction_status_in_a_response_raises(self):
        from unzer.model.payment import PaymentTransaction
        with pytest.raises(ValueError, match="half-done"):
            PaymentTransaction.fromDict({
                "type": "charge", "status": "half-done", "date": "2026-08-21 10:15:32",
                "amount": "1.0000", "participantId": "",
                "url": "https://api.unzer.com/v1/payments/s-pay-1/charges/s-chg-1",
            })

    def test_caller_typo_raises(self):
        with pytest.raises(TypeError):
            PaymentPage(action="chrage", amount=1.0, returnUrl="https://e.com/r")

    def test_salutation_unknown_is_a_real_value_not_a_placeholder(self):
        """The API sends it, and it carries meaning: no salutation is known."""
        from unzer.model.customer import Salutation
        customer = Customer(firstname="A", lastname="B", salutation=Salutation.UNKNOWN)
        assert customer.serialize()["salutation"] == "unknown"

    @staticmethod
    def _transaction(wire_type):
        from unzer.model.payment import PaymentTransaction
        return PaymentTransaction.fromDict({
            "type": wire_type, "status": "success", "date": "2026-08-21 10:15:32",
            "amount": "50.0000", "participantId": "",
            "url": "https://api.unzer.com/v1/payments/s-pay-1/charges/s-chg-1/cancels/s-cnl-1",
        })


class TestAmountRounding:
    """The API takes Decimal{10,4}. Floats do not cooperate."""

    def test_floating_point_residue_becomes_zero(self):
        """12.3 - 10.0 - 2.3 is 8.88e-16, and json.dumps writes that in scientific
        notation -- which is not a number this API accepts."""
        import json

        from unzer.model import SepaDirectDebit
        residue = 12.3 - 10.0 - 2.3
        assert residue != 0, "precondition: this is the IEEE-754 residue"
        request = PaymentRequest(paymentType=SepaDirectDebit(key="s-sdd-1"), amount=residue)
        assert request.serialize()["amount"] == 0.0
        assert "e-" not in json.dumps(request.serialize())

    def test_amount_is_capped_at_four_decimals(self):
        from unzer.model import SepaDirectDebit
        request = PaymentRequest(paymentType=SepaDirectDebit(key="s-sdd-1"), amount=1.23456789)
        assert request.serialize()["amount"] == 1.2346

    def test_paypage_amount_is_rounded(self):
        page = PaymentPage(action=Action.CHARGE, amount=1.23456789,
                           returnUrl="https://e.com/r")
        assert page.serialize()["amount"] == 1.2346

    @pytest.mark.parametrize("field", ["amountTotalGross", "amountTotalVat",
                                       "amountTotalDiscount"])
    def test_basket_v1_amounts_are_rounded(self, field):
        from unzer.model import Basket
        basket = Basket(**{field: 1.23456789}, currencyCode="EUR")
        assert basket.serialize()[field] == 1.2346

    def test_basket_v3_amount_is_rounded(self):
        from unzer.model import Basket
        basket = Basket(totalValueGross=1.23456789, currencyCode="EUR")
        assert basket.serialize()["totalValueGross"] == 1.2346

    @pytest.mark.parametrize("value,expected", [
        (None, None), ("", None), ("1.5500", 1.55), (2, 2.0), (0, 0.0),
    ])
    def test_round_amount_edge_cases(self, value, expected):
        from unzer.utils import roundAmount
        assert roundAmount(value) == expected

    def test_amounts_arrive_as_strings_from_the_api(self, fixture_json, client):
        """Every amount in a response is a string with four decimals."""
        raw = fixture_json("charge")
        assert isinstance(raw["amount"], str)
        from unzer.model.payment import PaymentResponse
        assert PaymentResponse.fromDict(raw, client).amount == 100.0


class TestInstallmentPlansTimestamp:
    """getPaylaterInstallmentPlans() raised on every single call.

    `expiresAt` was read as seconds because that is what the API reference shows
    (`1735689599`, ten digits). The API answers with thirteen digits, milliseconds,
    which lands in the year 58608 -- and this call is the first step of every
    installment flow.
    """

    def test_milliseconds_are_parsed(self, fixture_json):
        import datetime

        from unzer.model import InstallmentPlans
        plans = InstallmentPlans.fromDict(fixture_json("installment_plans"))
        assert plans.expiresAt == datetime.datetime.fromtimestamp(1787349029.678)

    def test_seconds_are_still_parsed(self, fixture_json):
        """The reference shows seconds, so both units have to work."""
        import datetime

        from unzer.model import InstallmentPlans
        data = fixture_json("installment_plans") | {"expiresAt": "1735689599"}
        assert InstallmentPlans.fromDict(data).expiresAt == \
            datetime.datetime.fromtimestamp(1735689599)

    # Compared against fromtimestamp of the expected seconds rather than against a
    # year: asserting a year here would only be green in one time zone.
    @pytest.mark.parametrize("value,seconds", [
        ("1787349029678", 1787349029.678),   # milliseconds, as the API sends them
        (1787349029678, 1787349029.678),     # same, as a number
        ("1735689599", 1735689599),          # seconds, as the reference shows them
        (1735689599, 1735689599),
    ])
    def test_parse_timestamp_handles_both_units(self, value, seconds):
        import datetime

        from unzer.utils import parseTimestamp
        assert parseTimestamp(value) == datetime.datetime.fromtimestamp(seconds)

    @pytest.mark.parametrize("value", [None, ""])
    def test_missing_timestamp_stays_none(self, value):
        from unzer.utils import parseTimestamp
        assert parseTimestamp(value) is None

    def test_plans_are_parsed(self, fixture_json):
        from unzer.model import InstallmentPlans
        plans = InstallmentPlans.fromDict(fixture_json("installment_plans"))
        assert plans.inquiryId
        assert len(plans.plans) == 1
        assert plans.plans[0].numberOfRates == 3
        assert len(plans.plans[0].installmentRates) == 3
