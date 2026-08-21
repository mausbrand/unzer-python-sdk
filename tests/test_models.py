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
