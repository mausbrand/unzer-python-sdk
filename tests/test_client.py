"""Tests for the transport layer of :class:`unzer.UnzerClient`."""


import pytest
import requests
import responses

from unzer import UnzerClient, __version__
from unzer.model import ErrorResponse

BASE = "https://api.unzer.com/v1"


class TestRequestBuilding:
    """Headers, authentication and URL construction."""

    @responses.activate
    def test_uses_private_key_as_basic_auth_username(self, client):
        responses.add(responses.GET, f"{BASE}/keypair", json={"publicKey": "s-pub-x"})
        client.getKeyPair()
        auth = responses.calls[0].request.headers["Authorization"]
        assert auth.startswith("Basic ")

    @responses.activate
    def test_sends_user_agent_with_version(self, client):
        responses.add(responses.GET, f"{BASE}/keypair", json={})
        client.getKeyPair()
        assert responses.calls[0].request.headers["user-agent"] == f"unzer-python-sdk {__version__}"

    @responses.activate
    def test_language_becomes_accept_language(self):
        client = UnzerClient("s-priv-x", "s-pub-x", language="de")
        responses.add(responses.GET, f"{BASE}/keypair", json={})
        client.getKeyPair()
        assert responses.calls[0].request.headers["accept-language"] == "de"

    @responses.activate
    def test_client_ip_is_sent_as_clientip_header(self):
        # The API reference names this header x-CLIENTIP, but the API expects
        # CLIENTIP -- verified against the sandbox, see AGENTS.md.
        client = UnzerClient("s-priv-x", "s-pub-x", client_ip="203.0.113.7")
        responses.add(responses.GET, f"{BASE}/keypair", json={})
        client.getKeyPair()
        assert responses.calls[0].request.headers["CLIENTIP"] == "203.0.113.7"

    @responses.activate
    def test_no_clientip_header_without_client_ip(self, client):
        responses.add(responses.GET, f"{BASE}/keypair", json={})
        client.getKeyPair()
        assert "CLIENTIP" not in responses.calls[0].request.headers

    @responses.activate
    def test_api_version_can_be_overridden_per_request(self, client):
        responses.add(responses.GET, "https://api.unzer.com/v3/baskets/s-bsk-1",
                      json={"id": "s-bsk-1", "basketItems": []})
        client.getBasket("s-bsk-1", api_version="v3")
        assert "/v3/baskets/" in responses.calls[0].request.url

    @responses.activate
    def test_additional_headers_are_merged(self, client):
        responses.add(responses.GET, f"{BASE}/keypair", json={})
        client.request("keypair", "GET", additional_headers={"X-Extra": "1"})
        assert responses.calls[0].request.headers["X-Extra"] == "1"


class TestErrorHandling:

    @responses.activate
    def test_client_error_raises_error_response(self, client, fixture_json):
        payload = fixture_json("error_400")
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1", json=payload, status=400)
        with pytest.raises(ErrorResponse) as excinfo:
            client.getPayment("s-pay-1")
        error = excinfo.value
        assert error.statusCode == 400
        assert error.errorId == payload["id"]
        assert [e.code for e in error.errors] == ["API.320.200.145"]
        assert error.errors[0].merchantMessage == "Basket is already in use."

    @responses.activate
    def test_error_response_keeps_the_source_response(self, client, fixture_json):
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1",
                      json=fixture_json("error_400"), status=400)
        with pytest.raises(ErrorResponse) as excinfo:
            client.getPayment("s-pay-1")
        assert isinstance(excinfo.value.srcResponse, requests.Response)

    @responses.activate
    def test_success_status_with_error_flag_raises(self, client, fixture_json):
        """The API answers 2xx with an error payload -- documented behaviour."""
        charge = fixture_json("charge") | {"isError": True, "isSuccess": False}
        charge["errors"] = fixture_json("error_400")["errors"]
        charge["timestamp"] = "2026-08-21 10:15:32"
        charge["url"] = f"{BASE}/payments/s-pay-1/charges"
        responses.add(responses.POST, f"{BASE}/payments/charges", json=charge, status=200)
        from unzer.model import PaymentRequest, SepaDirectDebit
        payment_type = SepaDirectDebit(key="s-sdd-1", iban="DE89370400440532013000")
        with pytest.raises(ErrorResponse):
            client.charge(PaymentRequest(paymentType=payment_type, amount=1.0))


class TestRetryPolicy:
    """Only idempotent methods may be repeated -- Unzer has no idempotency keys."""

    def test_only_get_and_head_are_retryable(self, client):
        assert client.retryableMethods == ("GET", "HEAD")

    @responses.activate
    def test_get_is_retried_on_server_error(self, retrying_client, fixture_json):
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1", status=500)
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1", status=500)
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1", json=fixture_json("payment_get"))
        payment = retrying_client.getPayment("s-pay-1")
        assert payment.paymentId == "s-pay-123456"
        assert len(responses.calls) == 3

    @responses.activate
    def test_post_is_not_retried_on_server_error(self, retrying_client):
        """A repeated POST could charge a customer twice."""
        responses.add(responses.POST, f"{BASE}/customers", status=500)
        from unzer.model import Customer
        with pytest.raises(ErrorResponse):
            retrying_client.createCustomer(Customer(firstname="A", lastname="B"))
        assert len(responses.calls) == 1, "POST must not be repeated"

    @responses.activate
    def test_get_is_retried_on_timeout(self, retrying_client, fixture_json):
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1",
                      body=requests.exceptions.ConnectTimeout())
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1", json=fixture_json("payment_get"))
        assert retrying_client.getPayment("s-pay-1").paymentId == "s-pay-123456"
        assert len(responses.calls) == 2

    @responses.activate
    def test_post_raises_on_timeout_instead_of_retrying(self, retrying_client):
        responses.add(responses.POST, f"{BASE}/customers",
                      body=requests.exceptions.ReadTimeout())
        from unzer.model import Customer
        with pytest.raises(requests.exceptions.ReadTimeout):
            retrying_client.createCustomer(Customer(firstname="A", lastname="B"))
        assert len(responses.calls) == 1

    @responses.activate
    def test_connection_error_is_retried_for_get(self, retrying_client, fixture_json):
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1",
                      body=requests.exceptions.ConnectionError())
        responses.add(responses.GET, f"{BASE}/payments/s-pay-1", json=fixture_json("payment_get"))
        assert retrying_client.getPayment("s-pay-1").paymentId == "s-pay-123456"


class TestWebhooks:

    @responses.activate
    def test_list_webhooks_returns_a_list(self, client, fixture_json):
        responses.add(responses.GET, f"{BASE}/webhooks", json=fixture_json("webhooks_list"))
        hooks = client.listWebhooks()
        assert isinstance(hooks, list), "a map object can only be consumed once"
        assert len(hooks) == 2
        assert hooks[0].webhookId == "s-whk-1"

    @responses.activate
    def test_single_webhook_response_is_wrapped_in_a_list(self, client, fixture_json):
        responses.add(responses.POST, f"{BASE}/webhooks", json=fixture_json("webhook_single"))
        from unzer.model import Events, Webhook
        hooks = client.createWebhook(Webhook(url="https://shop.example.com/webhook",
                                             event=Events.CHARGE_SUCCEEDED))
        assert isinstance(hooks, list)
        assert len(hooks) == 1

    @responses.activate
    def test_delete_webhook_accepts_a_model(self, client):
        responses.add(responses.DELETE, f"{BASE}/webhooks/s-whk-1", json={"id": "s-whk-1"})
        from unzer.model import Webhook
        webhook = Webhook(url="https://shop.example.com/webhook", webhookId="s-whk-1")
        assert client.deleteWebhook(webhook) == "s-whk-1"


class TestTypeChecks:
    """The client rejects wrong argument types before spending a request."""

    @pytest.mark.parametrize("method,argument", [
        ("getError", 1),
        ("getPayment", 1),
        ("getPaymentPage", 1),
        ("createCustomer", "not-a-customer"),
        ("createBasket", "not-a-basket"),
        ("createPaymentType", "not-a-payment-type"),
    ])
    def test_wrong_type_raises_type_error(self, client, method, argument):
        with pytest.raises(TypeError):
            getattr(client, method)(argument)

    def test_create_customer_rejects_customer_with_key(self, client):
        from unzer.model import Customer
        with pytest.raises(TypeError, match="Call updateCustomer"):
            client.createCustomer(Customer(firstname="A", lastname="B", key="s-cst-1"))
