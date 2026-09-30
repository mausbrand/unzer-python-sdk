"""Tests for the model layer: serialisation, deserialisation and validation."""

import datetime

import pytest

from unzer.model import (
    Action,
    Address,
    Basket,
    BasketItem,
    Customer,
    Events,
    PaymentGetResponse,
    PaymentPage,
    PaymentPageResponse,
    PaymentRequest,
    PaymentState,
    PaymentType,
    PaymentTypes,
    TransactionStatus,
    Webhook,
)
from unzer.model.customer import Salutation

# Every concrete payment type the SDK ships, discovered the same way the client does.
PAYMENT_TYPE_CLASSES = sorted(set(PaymentType.get_subclasses()), key=lambda c: c.__name__)


class TestPaymentTypes:

    def test_sdk_ships_the_expected_number_of_types(self):
        assert len(PAYMENT_TYPE_CLASSES) == 24

    @pytest.mark.parametrize("cls", PAYMENT_TYPE_CLASSES, ids=lambda c: c.__name__)
    def test_every_type_declares_method_and_method_name(self, cls):
        """`method` is the short code (crd), `method_name` the URL slug (card)."""
        assert isinstance(cls.method, PaymentTypes)
        assert cls.method_name.value, f"{cls.__name__} has no URL slug"

    @pytest.mark.parametrize("cls", PAYMENT_TYPE_CLASSES, ids=lambda c: c.__name__)
    def test_from_dict_maps_id_to_key(self, cls):
        assert cls.fromDict({"id": "s-xxx-1"}).key == "s-xxx-1"

    @pytest.mark.parametrize("cls", PAYMENT_TYPE_CLASSES, ids=lambda c: c.__name__)
    def test_serialize_returns_a_dict(self, cls):
        assert isinstance(cls().serialize(), dict)

    def test_method_names_are_unique(self):
        slugs = [c.method_name.value for c in PAYMENT_TYPE_CLASSES]
        assert len(slugs) == len(set(slugs)), "two types claim the same URL slug"

    def test_construct_finds_the_class_for_a_short_code(self):
        assert PaymentType.construct(PaymentTypes.CARD).__name__ == "Card"

    def test_construct_builds_a_placeholder_for_unknown_types(self):
        cls = PaymentType.construct(PaymentTypes.GIROPAY)
        assert issubclass(cls, PaymentType)
        # The placeholder must not hand a bogus slug to the request builder.
        with pytest.raises(NotImplementedError):
            _ = cls.method_name.value


class TestBasket:
    """The basket has two incompatible schemas; the amount fields decide which."""

    def test_v1_is_used_without_total_value_gross(self, fixture_json):
        basket = Basket.fromDict(fixture_json("basket_v1"))
        assert not basket.isV3()
        assert basket.apiVersion == "v1"
        assert basket.amountTotalGross == 100.0

    def test_v3_is_used_with_total_value_gross(self, fixture_json):
        basket = Basket.fromDict(fixture_json("basket_v3"))
        assert basket.isV3()
        assert basket.apiVersion == "v3"
        assert basket.totalValueGross == 100.0

    def test_v1_serialisation_carries_the_v1_amounts(self):
        basket = Basket(amountTotalGross=100.0, amountTotalVat=15.97, currencyCode="EUR")
        data = basket.serialize()
        assert data["amountTotalGross"] == 100.0
        assert "totalValueGross" not in data

    def test_v3_serialisation_carries_only_the_v3_amount(self):
        basket = Basket(totalValueGross=100.0, currencyCode="EUR")
        data = basket.serialize()
        assert data["totalValueGross"] == 100.0
        assert "amountTotalGross" not in data

    def test_missing_amounts_stay_none(self):
        basket = Basket.fromDict({"id": "s-bsk-1", "currencyCode": "EUR"})
        assert basket.amountTotalGross is None
        assert basket.totalValueGross is None

    def test_basket_items_are_parsed(self, fixture_json):
        basket = Basket.fromDict(fixture_json("basket_v1"))
        assert len(basket.basketItems) == 1
        assert isinstance(basket.basketItems[0], BasketItem)
        assert basket.basketItems[0].title == "Custom print t-shirt"


class TestCustomer:

    def test_round_trip_from_api_response(self, fixture_json):
        customer = Customer.fromDict(fixture_json("customer"))
        assert customer.key == "s-cst-cd1e6a11c02a"
        assert customer.firstname == "Manuel"
        assert isinstance(customer.billingAddress, Address)
        assert customer.billingAddress.city == "Heidelberg"

    def test_addresses_are_objects_even_when_empty(self, fixture_json):
        """The API answers with an empty address object, never with a string."""
        customer = Customer.fromDict({
            **fixture_json("customer"),
            "billingAddress": {"name": "", "street": "", "state": "", "zip": "",
                               "city": "", "country": ""},
        })
        assert isinstance(customer.billingAddress, Address)
        assert customer.billingAddress.city == ""

    @pytest.mark.parametrize("value,expected", [
        ("1990-01-24", datetime.datetime(1990, 1, 24)),
        ("24.01.1990", datetime.datetime(1990, 1, 24)),
        (datetime.date(1990, 1, 24), datetime.date(1990, 1, 24)),
        (None, None),
        ("", None),
    ])
    def test_birth_date_accepts_both_formats(self, value, expected):
        assert Customer(firstname="A", lastname="B", birthDate=value).birthDate == expected

    def test_invalid_birth_date_raises(self):
        with pytest.raises(TypeError):
            Customer(firstname="A", lastname="B", birthDate="24/01/1990")

    def test_serialised_birth_date_is_iso(self):
        customer = Customer(firstname="A", lastname="B", birthDate="24.01.1990")
        assert customer.serialize()["birthDate"] == "1990-01-24"

    @pytest.mark.parametrize("value", [Salutation.MR, Salutation.MRS, Salutation.UNKNOWN])
    def test_valid_salutations(self, value):
        assert Customer(firstname="A", lastname="B", salutation=value).salutation == value

    def test_invalid_salutation_raises(self):
        with pytest.raises(TypeError):
            Customer(firstname="A", lastname="B", salutation="herr")

    def test_missing_salutation_defaults_to_unknown(self):
        assert Customer(firstname="A", lastname="B").salutation == Salutation.UNKNOWN

    def test_key_or_customer_id_prefers_the_key(self):
        customer = Customer(firstname="A", lastname="B", key="s-cst-1", customerId="mine")
        assert customer.keyOrCustomerId == "s-cst-1"

    @pytest.mark.parametrize("attr", ["firstname", "lastname"])
    def test_the_two_names_are_limited_separately(self, attr):
        """Unlike an address, a customer sends them as two fields with a limit each."""
        names = {"firstname": "A", "lastname": "B"}
        assert Customer(**{**names, attr: "x" * 40}).validateBeforeRequest()
        with pytest.raises(ValueError, match=rf"Customer\.{attr}"):
            Customer(**{**names, attr: "x" * 41}).validateBeforeRequest()

    def test_the_addresses_are_validated_too(self):
        """Nothing else would: they only ever travel inside a customer request."""
        customer = Customer(
            firstname="A", lastname="B",
            billingAddress=Address(firstname="Max", lastname="Mustermann", city="x" * 31),
        )
        with pytest.raises(ValueError, match=r"Address\.city"):
            customer.validateBeforeRequest()

    def test_the_customer_and_address_limits_line_up(self):
        """Two customer names at their maximum join into an address name at its maximum.

        40 + 1 + 40 is exactly 81, so a customer that satisfies its own two field
        limits can never break the address one. That the measurements agree this
        precisely is a good sign they are right; if either constant is ever changed
        without the other, this is where it shows.
        """
        names = {
            "firstname": "x" * Customer.MAX_LENGTHS["firstname"],
            "lastname": "y" * Customer.MAX_LENGTHS["lastname"],
        }
        assert len(Address(**names).name) == Address.MAX_LENGTHS["name"]
        assert Customer(**names, billingAddress=Address(**names)).validateBeforeRequest()


class TestAddress:

    def test_name_is_split_into_first_and_lastname(self):
        address = Address.fromDict({"name": "Manuel Weissmann", "street": "", "state": "",
                                   "zip": "", "city": "", "country": ""})
        assert (address.firstname, address.lastname) == ("Manuel", "Weissmann")

    def test_single_word_name_leaves_lastname_empty(self):
        address = Address.fromDict({"name": "Prince", "street": "", "state": "",
                                    "zip": "", "city": "", "country": ""})
        assert address.firstname == "Prince"
        assert address.lastname is None

    def test_serialisation_joins_the_name_and_renames_zip(self):
        data = Address(firstname="Max", lastname="Mustermann", zipCode="10963").serialize()
        assert data["name"] == "Max Mustermann"
        assert data["zip"] == "10963", "the wire format calls it zip, not zipCode"

    @pytest.mark.parametrize(("firstname", "lastname"), [
        ("a" * 40, "b" * 40),  # balanced
        ("a", "b" * 79),       # nearly all of it in the last name
        ("a" * 79, "b"),       # and the other way round
    ])
    def test_a_name_of_exactly_the_limit_passes(self, firstname, lastname):
        address = Address(firstname=firstname, lastname=lastname)
        assert len(address.name) == 81
        assert address.validateBeforeRequest()

    @pytest.mark.parametrize(("firstname", "lastname"), [
        ("a" * 41, "b" * 40),
        ("a", "b" * 80),       # neither half is long by itself -- their sum is
        ("a" * 80, "b"),
    ])
    def test_a_name_over_the_limit_is_rejected_whichever_half_is_long(self, firstname, lastname):
        with pytest.raises(ValueError, match=r"Address\.name"):
            Address(firstname=firstname, lastname=lastname).validateBeforeRequest()

    def test_the_joining_space_counts_towards_the_limit(self):
        """41 and 40 are 81 characters of name, but 82 go over the wire."""
        with pytest.raises(ValueError, match="82 characters"):
            Address(firstname="a" * 41, lastname="b" * 40).validateBeforeRequest()

    @pytest.mark.parametrize(("attr", "limit"), [("street", 64), ("zipCode", 10), ("city", 30)])
    def test_field_limits(self, attr, limit):
        name = {"firstname": "Max", "lastname": "Mustermann"}
        assert Address(**name, **{attr: "x" * limit}).validateBeforeRequest()
        with pytest.raises(ValueError, match=rf"Address\.{attr}"):
            Address(**name, **{attr: "x" * (limit + 1)}).validateBeforeRequest()

    def test_a_missing_value_is_not_a_length_problem(self):
        assert Address(firstname="Max", lastname="Mustermann", city=None).validateBeforeRequest()


class TestPaymentGetResponse:

    def test_round_trip(self, fixture_json, client):
        payment = PaymentGetResponse.fromDict(fixture_json("payment_get"), client)
        assert payment.paymentId == "s-pay-123456"
        assert payment.state is PaymentState.COMPLETED
        assert payment.amountTotal == 100.0
        assert payment.paymentType is PaymentTypes.CARD

    def test_transactions_carry_enums_not_strings(self, fixture_json, client):
        payment = PaymentGetResponse.fromDict(fixture_json("payment_get"), client)
        assert [t.action for t in payment.transactions] == [Action.AUTHORIZE, Action.CHARGE]
        assert all(t.status is TransactionStatus.SUCCESS for t in payment.transactions)

    def test_transaction_ids_are_parsed_from_the_url(self, fixture_json, client):
        payment = PaymentGetResponse.fromDict(fixture_json("payment_get"), client)
        assert [t.transactionId for t in payment.transactions] == ["s-aut-1", "s-chg-1"]

    def test_payment_type_from_type_id(self):
        assert PaymentGetResponse.getPaymentTypeFromTypeId("s-crd-abc") is PaymentTypes.CARD

    @pytest.mark.parametrize("type_id", ["", None, "nonsense", "s-xyz-abc"])
    def test_invalid_type_id_raises(self, type_id):
        with pytest.raises(ValueError):
            PaymentGetResponse.getPaymentTypeFromTypeId(type_id)

    def test_response_models_do_not_serialise(self, fixture_json, client):
        payment = PaymentGetResponse.fromDict(fixture_json("payment_get"), client)
        with pytest.raises(NotImplementedError):
            payment.serialize()


class TestPaymentRequest:

    def test_serialisation_nests_the_resource_ids(self):
        from unzer.model import Card
        request = PaymentRequest(paymentType=Card(key="s-crd-1"), amount=10.0,
                                 customerId="s-cst-1", basketId="s-bsk-1")
        data = request.serialize()
        assert data["resources"] == {
            "customerId": "s-cst-1", "typeId": "s-crd-1",
            "metadataId": None, "basketId": "s-bsk-1",
        }

    def test_currency_defaults_to_eur(self):
        assert PaymentRequest().currency == "EUR"

    def test_card3ds_must_be_boolean_or_none(self):
        with pytest.raises(TypeError):
            PaymentRequest(card3ds="yes")

    def test_payment_type_is_required_before_a_request(self):
        with pytest.raises(ValueError, match="paymentType"):
            PaymentRequest().validateBeforeRequest()


class TestPaymentPage:

    def test_round_trip_from_api_response(self, fixture_json):
        page = PaymentPageResponse.fromDict(fixture_json("paypage"))
        assert page.payPageId == "s-ppg-1"
        assert page.action is Action.CHARGE
        assert page.paymentId == "s-pay-15"

    @pytest.mark.parametrize("value", ["CHARGE", "charge", Action.CHARGE])
    def test_action_accepts_both_casings_and_the_enum(self, value):
        page = PaymentPage(action=value, amount=1.0, returnUrl="https://e.com/r")
        assert page.action is Action.CHARGE

    def test_invalid_action_raises(self):
        with pytest.raises(TypeError):
            PaymentPage(action="nonsense", amount=1.0, returnUrl="https://e.com/r")

    def test_required_attributes_are_checked(self):
        page = PaymentPage(action=Action.CHARGE, amount=None, returnUrl="https://e.com/r")
        with pytest.raises(ValueError, match="amount"):
            page.validateBeforeRequest()


class TestWebhook:

    def test_a_single_event_becomes_a_list(self):
        assert Webhook(url="https://e.com/h", event=Events.CHARGE).event == [Events.CHARGE]

    def test_plain_strings_are_accepted(self):
        webhook = Webhook(url="https://e.com/h", event="charge.succeeded")
        assert webhook.event == [Events.CHARGE_SUCCEEDED]

    @pytest.mark.parametrize("value", ["nonsense", "unzer.model.webhook", "__module__"])
    def test_invalid_events_are_rejected(self, value):
        with pytest.raises(TypeError):
            Webhook(url="https://e.com/h", event=value)

    def test_serialisation_uses_event_list(self):
        webhook = Webhook(url="https://e.com/h", event=[Events.CHARGE, Events.PAYMENT])
        assert webhook.serialize() == {
            "eventList": [Events.CHARGE, Events.PAYMENT],
            "url": "https://e.com/h",
        }

    def test_url_is_required(self):
        with pytest.raises(ValueError, match="url"):
            Webhook(url=None).validateBeforeRequest()
