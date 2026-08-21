import logging
import time
import typing as t
from types import NoneType
from urllib.parse import urlencode

import requests

from . import __version__
from .model import *
from .model.basket import Basket
from .model.installment_plans import InstallmentPlans
from .model.payment import PaymentGetResponse, PaymentRequest, PaymentResponse
from .model.payment_type import PaylaterInstallment
from .model.paymentpage import PaymentPage, PaymentPageResponse
from .model.risk_check import RiskCheckResponse
from .model.webhook import Webhook

logger = logging.getLogger("unzer-sdk").getChild(__name__)

HttpMethod = t.Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class UnzerClient:
    endpoint = "https://api.unzer.com"
    """Base URL of the API, without the version segment."""

    apiVersion = "v1"
    """Default API version, used unless a request asks for another one."""

    retryDelays = (1, 2, 4, 8)
    """Delays in seconds between the retries of a failed request.

    Only applies to the methods in :attr:`retryableMethods`.
    """

    retryableMethods = ("GET", "HEAD")
    """HTTP methods that may be retried after a timeout or a server error.

    Deliberately excludes POST, PUT and DELETE. A timed out POST may well have been
    carried out by the API with only the response getting lost, so repeating it can
    charge a customer twice -- and the Unzer API offers no idempotency key to guard
    against that (there is none in either of its OpenAPI specs). A failed write is
    therefore raised to the caller, who can look the payment up by ``orderId`` and
    decide.
    """

    timeout = 30
    """Timeout in seconds of a single request.

    Kept well above the response time of a plain payment call: the Pay later
    methods run a credit check while the request is open, which regularly takes
    more than ten seconds. A request that times out is retried, and repeating a
    payment call is not free of consequences -- the second attempt runs into an
    already used basket at best.
    """

    def __init__(
            self,
            private_key: str,
            public_key: str,
            sandbox: bool = False,
            language: str = "en",
            client_ip: str = None,
            timeout: int = None,
    ):
        """Create a new client for the unzer-api.

        :param private_key: The private key of the keypair.
        :param public_key: The public key of the keypair.
        :param sandbox: (optional) Mark this client as working on a sandbox account.

            This does **not** change the endpoint: whether a request hits the
            sandbox or production is decided by the key alone (``s-`` versus ``p-``
            prefix), and ``api.unzer.com`` serves both. The flag is kept because
            consumers need to know which mode they are in -- among other things the
            redirect URLs Unzer returns differ (``sbx-payment.unzer.com`` versus
            ``payment.unzer.com``).
        :param language: (optional) Language for translations of customer messages.
        :param client_ip: (optional) IP address of the customer.
            Sent as ``CLIENTIP`` header with every request.
            Required by the Pay later payment methods (e.g. installment)
            for their risk checks.
            The API documentation names this header ``x-CLIENTIP``,
            but both the PHP and the Java SDK send it as ``CLIENTIP``.
        :param timeout: (optional) Timeout in seconds of a single request,
            overrides :attr:`timeout`.
        """
        super().__init__()
        self.private_key = private_key
        self.public_key = public_key
        self.sandbox = sandbox
        self.language = language
        self.client_ip = client_ip
        if timeout is not None:
            self.timeout = timeout

    def request(
            self,
            operation: str,
            method: HttpMethod,
            payload: t.Any = None,
            additional_headers: dict[str, str] = None,
            api_version: str = None,
    ) -> t.Any:
        """Perform a request to the unzer-api.

        This method does not really perform the request itself,
        but rather prepares the request for :meth:`_request`.

        :param operation: The method on the REST API (URL path).
        :param method: The HTTP method (e.g. POST, GET).
        :param payload: The payload for this request.
            Send json-encoded as body.
        :param additional_headers: Additional headers for this request.
        :param api_version: (optional) The API version to use for this request.
            Defaults to :attr:`apiVersion` (``v1``).
            Some resources are only available in a newer version
            (e.g. baskets for the Pay later payment methods).
        :return: The json-decoded response from the api.
        """
        url = "%s/%s/%s" % (self.endpoint, api_version or self.apiVersion, operation)
        headers = {
            "user-agent": "unzer-python-sdk %s" % __version__,
            "content-type": "application/json; charset=UTF-8",
            "accept": "application/json",
            "accept-language": self.language,  # language for translation of customerMessage in errors
        }
        if self.client_ip:
            headers["CLIENTIP"] = self.client_ip
        if additional_headers:
            headers |= additional_headers
        return self._request(
            url,
            method,
            headers,
            payload,
            auth=(self.private_key, "")
        )

    def _request(self, url: str, method: str,
                 headers: list[tuple] | dict[str, str], payload: t.Any,
                 auth: tuple[str, str]) -> t.Any:
        """Helper method to perform the request with throttling.

        :param url: The complete URL.
        :param method: The HTTP method (e.g. POST, GET).
        :param headers: The HTTP headers.
        :type headers: list[tuple] | dict[str, str]
        :param payload: The HTTP payload (will be json encoded).
        :param auth: The authentication for this request.
        :return: The json decoded response

        :raises: :exc:`ErrorResponse` in case of an client error
            or after last retry failed.
        """
        r = None
        retryable = method.upper() in self.retryableMethods
        delays = (0,) + (self.retryDelays if retryable else ())
        for idx, delay in enumerate(delays):
            logger.debug("Perform try no. %d (delay: %d)", idx, delay)
            time.sleep(delay)
            logger.debug("%s %s", method, url)
            logger.debug("payload: %r", payload)
            logger.debug("headers: %r", headers)
            try:
                r = requests.request(
                    method,
                    url,
                    json=payload,
                    headers=headers,
                    auth=auth,
                    verify=True,
                    timeout=self.timeout,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                # Timeout covers both ConnectTimeout and ReadTimeout.
                logger.exception("Request failed on the transport level")
                if not retryable:
                    raise
                continue
            if 200 <= r.status_code <= 201:
                logger.debug("Response[%s %s]: %r", r.status_code, r.reason, r.json())
                return r.json()
            if 500 <= r.status_code < 600:
                logger.debug("Server error")
                logger.debug("Response[%s %s]: %r", r.status_code, r.reason, r.text)
                if not retryable:
                    break
                continue
            logger.debug("Client error")
            logger.debug("Response[%s %s]: %r", r.status_code, r.reason, r.text)
            errorResponse = ErrorResponse.fromDict(r.json())
            errorResponse.statusCode = r.status_code
            errorResponse.srcResponse = r
            raise errorResponse

        logger.error("All request attempts failed")
        if r is not None:
            try:
                errorResponse = ErrorResponse.fromDict(r.json(), "All request attempts failed")
                errorResponse.statusCode = r.status_code
                errorResponse.srcResponse = r
            except ValueError:
                logger.exception("Failed to build an ErrorResponse from last request")
            else:
                raise errorResponse
        raise ErrorResponse("All request attempts failed", srcResponse=r)

    def getKeyPair(self) -> dict:
        """Provide the public key of the used private key
        as well as a list of the payment types available for the merchant.

        :return: The fetched KeyPairResponse
        """
        # ToDo: implement KeyPairResponse-model
        return self.request(
            "keypair",
            "GET",
        )

    def getKeyPairTypes(self) -> dict[str, t.Any]:
        """Get detailed information and payment method configuration

        The endpoint provides details about the key pairs configured for a merchant account
        and the payment methods they support, including their associated public key, private key,
        currencies, and customer types (like B2C or B2B).

        .. seealso::

            - https://api.unzer.com/api-reference/index.html#tag/Keypair/operation/getAvailablePaymentMethodTypesWithTypeInformation  # noqa: E501
            - https://docs.unzer.com/server-side-integration/direct-api-integration/manage-api-resources/api-check-key-configuration/  # noqa: E501

        :return: The fetched KeyPairTypesResponse
        """
        # ToDo: implement KeyPairResponse-model
        return self.request(
            "keypair/types",
            "GET",
        )

    def getError(self, errorId: str) -> dict:
        """Get information about an error

        :param errorId: The error id (e.g. p-err-abcdefghij1234567rstuvwyxyz)
        """
        if not isinstance(errorId, str):
            raise TypeError("Expected a errorId of type str. Got %r" % type(errorId))
        return self.request(
            "errors/%s" % errorId,
            "GET",
        )

    def createCustomer(self, customer):
        """Creating a customer

        :param customer: Customer object
        :type customer: Customer
        :return: The created customer object
        :rtype: Customer
        """
        if not isinstance(customer, Customer):
            raise TypeError("Expected a Customer object. Got %r" % type(customer))
        if customer.key:
            raise TypeError("Customer has a id (key) set. "
                            "Call updateCustomer to update it or remove it to create a new one.")
        data = self.request(
            "customers",
            "POST",
            customer.serialize(),
        )
        # API docs wrong: we get only a dict with the id back
        return self.getCustomer(data["id"])

    def updateCustomer(self, customer):
        """Update a customer using unique customerId or the resource id from the customers resource.
        The customer MUST have customerId oder key (id)

        :param customer: Customer object
        :type customer: Customer
        :return: The updated customer object
        :rtype: Customer
        """
        if not isinstance(customer, Customer):
            raise TypeError("Expected a Customer object. Got %r" % type(customer))
        if not customer.keyOrCustomerId:
            raise TypeError("Customer has no customerId oder key (id)")
        data = self.request(
            "customers/%s" % customer.keyOrCustomerId,
            "PUT",
            customer.serialize(),
        )
        # API docs wrong: we get only a dict with the id back
        return self.getCustomer(data["id"])

    def createOrUpdateCustomer(self, customer):
        try:
            return self.createCustomer(customer)
        except ErrorResponse as er:
            if er.errors and er.statusCode == 400 and er.errors[0].code == "API.410.200.010":
                return self.updateCustomer(customer)
            raise er

    def deleteCustomer(self, customer):
        """Delete a customer using unique customerId or the resource id from the customers resource.
        The customer MUST have customerId oder key (id)

        :param customer: Customer object, customerId or id (key)
        :type customer: Customer or str
        :return: The id of the customer
        :rtype: str
        """
        if isinstance(customer, Customer):
            if not customer.key and not customer.customerId:
                raise TypeError("Customer has no customerId oder key (id)")
            codeOrExternalId = customer.customerId or customer.key
        elif isinstance(customer, str):
            codeOrExternalId = customer
        else:
            raise TypeError("Expected a Customer object or str. Got %r" % type(customer))
        data = self.request(
            "customers/%s" % codeOrExternalId,
            "DELETE",
        )
        return data["id"]

    def getCustomer(self, codeOrExternalId):
        """Fetch a customer using unique customerId or the resource id from the customers resource.

        :param codeOrExternalId: customerId or id (key)
        :type codeOrExternalId: str
        :return: The fetched customer object
        :rtype: Customer
        """
        data = self.request(
            "customers/%s" % codeOrExternalId,
            "GET",
        )
        return Customer.fromDict(data)

    def createBasket(self, basket):
        """Creating a basket

        :param basket: Basket object
        :type basket: Basket
        :return: The created Basket object
        :rtype: Basket
        """
        if not isinstance(basket, Basket):
            raise TypeError("Expected a Basket object. Got %r" % type(basket))
        data = self.request(
            "baskets",
            "POST",
            basket.serialize(),
            api_version=basket.apiVersion,
        )
        return self.getBasket(data["id"], api_version=basket.apiVersion)

    def updateBasket(self, basket):
        """Update a basket.
        The basket MUST have key (id)

        :param basket: Basket object
        :type basket: Basket
        :return: The updated basket object
        :rtype: Basket
        """
        if not isinstance(basket, Basket):
            raise TypeError("Expected a Basket object. Got %r" % type(basket))
        if not basket.key:
            raise TypeError("Basket has no key (id)")
        data = self.request(
            "baskets/%s" % basket.key,
            "PUT",
            basket.serialize(),
            api_version=basket.apiVersion,
        )
        return self.getBasket(data["id"], api_version=basket.apiVersion)

    def getBasket(self, basketId, api_version: str = None):
        """Fetch a basket.

        :param basketId: basket's id (key)
        :type basketId: str
        :param api_version: (optional) The API version of the basket schema to fetch.
            A basket created with the v3 schema should also be fetched with ``v3``.
        :return: The fetched basket object
        :rtype: Basket
        """
        data = self.request(
            "baskets/%s" % basketId,
            "GET",
            api_version=api_version,
        )
        return Basket.fromDict(data)

    def createPaymentType(self, paymentType):
        """Create a new PaymentType at Unzer.

        This can be any Object which inherits the abstract class PaymentType.

        :param paymentType: The PaymentPage model
        :type paymentType: PaymentType
        :return: The paymentType response
        :rtype: PaymentType
        """
        if not isinstance(paymentType, PaymentType):
            raise TypeError("Expected a PaymentType object. Got %r" % type(paymentType))
        paymentType.validateBeforeRequest()
        data = self.request(
            "types/%s" % paymentType.method_name.value,
            "POST",
            paymentType.serialize(),
        )
        return type(paymentType).fromDict(data)

    def getPaylaterInstallmentPlans(
            self,
            amount: float,
            currency: str,
            country: str,
            customerType: str = None,
            orderId: str = None,
            startDateOfPurchase: str = None,
            endDateOfPurchase: str = None,
            nominalInterest: str = None,
    ) -> InstallmentPlans:
        """Fetch the available installment plans for a purchase.

        This is the first step of an installment payment: the plans must be presented to
        the customer, and the :attr:`~unzer.model.InstallmentPlans.inquiryId` of the
        response is required to create the
        :class:`~unzer.model.PaylaterInstallment` payment type.

        .. seealso:: https://docs.unzer.com/payment-methods/installment/accept-unzer-installment-server-side-only-integration/  # noqa: E501

        :param amount: Total amount of the purchase.
        :param currency: ISO currency code of the transaction (``EUR`` or ``CHF``).
        :param country: The customer's country in ISO 3166 ALPHA-2 format (e.g. ``DE``).
        :param customerType: (optional) ``B2C`` (``B2B`` is not available yet).
        :param orderId: (optional) Order id that identifies the payment on merchant side.
        :param startDateOfPurchase: (optional) Start date of the purchase.
        :param endDateOfPurchase: (optional) End date of the purchase.
        :param nominalInterest: (optional) Nominal interest rate as percentage.
        :return: The available plans
        """
        query = {
            "amount": amount,
            "currency": currency,
            "country": country,
        }
        for key, value in (
                ("customerType", customerType),
                ("orderId", orderId),
                ("startDateOfPurchase", startDateOfPurchase),
                ("endDateOfPurchase", endDateOfPurchase),
                ("nominalInterest", nominalInterest),
        ):
            if value is not None:
                query[key] = value
        data = self.request(
            "types/%s/plans?%s" % (PaylaterInstallment.method_name.value, urlencode(query)),
            "GET",
        )
        return InstallmentPlans.fromDict(data)

    def riskCheckPaylaterInstallment(
            self,
            payment: PaymentRequest,
            client_ip: str = None,
    ) -> RiskCheckResponse:
        """Perform a risk check for an installment payment.

        This optional call evaluates the customer data before the order is placed,
        so the customer gets the feedback before finishing the checkout.
        It is not part of the payment process itself.

        The request requires the customer, basket and paymentType resources
        of the intended payment, therefore it takes the same
        :class:`~unzer.model.PaymentRequest` as :meth:`authorize`.

        .. note::
            The endpoint is part of the API reference (``/v1/types/paylater-installment/risk-check``),
            but implemented in neither the PHP nor the Java SDK,
            so the payload could only be taken from the documentation.

        .. seealso:: https://docs.unzer.com/payment-methods/installment/accept-unzer-installment-server-side-only-integration/  # noqa: E501

        :param payment: The PaymentRequest model of the intended payment.
        :param client_ip: (optional) IP address of the customer,
            sent as ``CLIENTIP`` header. Falls back to the client's
            :attr:`client_ip`, which is required by this endpoint.
        :return: The result of the risk check
        :raises ErrorResponse: If the risk check was declined.
        """
        if not isinstance(payment, PaymentRequest):
            raise TypeError("Expected a PaymentRequest object. Got %r" % type(payment))
        if not payment.paymentType or not payment.paymentType.key:
            raise ValueError("The paymentType must be created before the risk check")
        payment.validateBeforeRequest()
        data = self.request(
            "types/%s/risk-check" % PaylaterInstallment.method_name.value,
            "POST",
            payment.serialize(),
            additional_headers={"CLIENTIP": client_ip} if client_ip else None,
        )
        if data.get("isError"):
            raise ErrorResponse.fromDict(data)
        return RiskCheckResponse.fromDict(data)

    def createPaymentPage(self, paymentPage):
        """The initialize payment page call with direct charge purpose.

        :param paymentPage: The PaymentPage model
        :type paymentPage: PaymentPage
        :return: The PaymentPageResponse
        :rtype: PaymentPageResponse
        """
        if not isinstance(paymentPage, PaymentPage) or isinstance(paymentPage, PaymentPageResponse):
            raise TypeError("Expected a PaymentPage object. Got %r" % type(paymentPage))
        paymentPage.validateBeforeRequest()
        data = self.request(
            f"paypage/{paymentPage.action.value}",
            "POST",
            paymentPage.serialize(),
        )
        return PaymentPageResponse.fromDict(data)

    def getPaymentPage(self, payPageId):
        """Fetch the payment resource. Provides an overview about a payment.

        :param payPageId: The related payment page id.
        :type payPageId: str
        :return: The PaymentPage ressource
        :rtype: PaymentPageResponse
        """
        if not isinstance(payPageId, str):
            raise TypeError("Expected a payPageId of type str. Got %r" % type(payPageId))
        data = self.request(
            "paypage/%s" % payPageId,
            "GET",
        )
        return PaymentPageResponse.fromDict(data)

    def getPayment(self, codeOrOrderId):
        """Fetch the payment resource. Provides an overview about a payment.

        :param codeOrOrderId: The id of the order
        :type codeOrOrderId: str
        :return: Payment ressource
        :rtype: PaymentGetResponse
        """
        if not isinstance(codeOrOrderId, str):
            raise TypeError("Expected a codeOrOrderId of type str. Got %r" % type(codeOrOrderId))
        data = self.request(
            "payments/%s" % codeOrOrderId,
            "GET",
        )
        return PaymentGetResponse.fromDict(data, self)

    def authorize(self, payment, **kwargs) -> PaymentResponse:
        """Authorize call for redirect payments.

        The paymentType will be created within this method,
        if not already created.

        :param payment: The PaymentRequest model
        :type payment: PaymentRequest
        :return: The paymentType response
        :rtype: PaymentResponse
        """
        return self._authorize_or_charge("authorize", payment, **kwargs)

    def charge(self, payment, **kwargs):
        """Charge call for redirect payments.

        The paymentType will be created within this method,
        if not already created.

        :param payment: The PaymentRequest model
        :type payment: PaymentRequest
        :return: The paymentType response
        :rtype: PaymentResponse
        """
        return self._authorize_or_charge("charges", payment, **kwargs)

    def _authorize_or_charge(
            self,
            type_: str,
            payment: PaymentRequest,
            headers: dict[str, str] = None,
    ) -> PaymentResponse:
        """Internal helper for authorize and charge calls
        """
        if type_ not in {"authorize", "charges"}:
            raise ValueError("Invalid type %r" % type_)
        if not isinstance(payment, PaymentRequest):
            raise TypeError("Expected a PaymentRequest object. Got %r" % type(PaymentRequest))
        if not payment.paymentType:
            raise ValueError("No paymentType set")
        if not payment.paymentType.key:
            payment.paymentType = self.createPaymentType(payment.paymentType)
        payment.validateBeforeRequest()
        data = self.request(
            "/".join(filter(None, ["payments", payment.paymentId, type_])),
            "POST",
            payment.serialize(),
            additional_headers=headers or {},
        )
        if data.get("isError"):
            raise ErrorResponse.fromDict(data)
        return PaymentResponse.fromDict(data, self)

    def getChargedTransaction(self, codeOrOrderId, txnCode):
        """Fetch the corresponding charged transaction.
        The first found charged transaction will be returned if the <txnCode> = null.

        :param codeOrOrderId: The id of the payment
        :type codeOrOrderId: str
        :param txnCode: The id of the transaction
        :type txnCode: str

        :return: PaymentResponse ressource
        :rtype: PaymentResponse
        """
        if not isinstance(codeOrOrderId, str):
            raise TypeError("Expected a codeOrOrderId of type str. Got %r" % type(codeOrOrderId))
        if not isinstance(txnCode, (str, NoneType)):
            raise TypeError("Expected a txnCode of type str or None. Got %r" % type(txnCode))
        data = self.request(
            "payments/%s/charges/%s" % (codeOrOrderId, txnCode or ""),
            "GET",
        )
        return PaymentResponse.fromDict(data, self)

    def listWebhooks(self):
        """Get all webhook resources.

        :return: A list of Webhooks
        :rtype: list[Webhook]
        """
        data = self.request(
            "webhooks",
            "GET",
        )
        return self._loadWebhookResponse(data)

    def getWebhook(self, webhookId):
        """Get one specific webhook resource.

        :param webhookId: The id of the webhook.
        :type webhookId: str
        :return: The webhook resource.
        :rtype: Webhook
        """
        data = self.request(
            "webhooks/%s" % webhookId,
            "GET",
        )
        return Webhook.fromDict(data)

    def createWebhook(self, webhook):
        """Create a new webhook.

        :param webhook: The webhook mode
        :return: A list of created Webhooks models (each for each event-type)
        :rtype: list[Webhook]
        """
        if not isinstance(webhook, Webhook):
            raise TypeError("Expected a Webhook object. Got %r" % type(webhook))
        if webhook.webhookId:
            raise TypeError("Webhook has a id set. "
                            "Call updateWebhook to update it or remove the id to create a new one.")
        webhook.validateBeforeRequest()
        data = self.request(
            "webhooks",
            "POST",
            webhook.serialize(),
        )
        return self._loadWebhookResponse(data)

    def updateWebhook(self, webhook):
        """Update the URL for an existing webhook.
        Will not change the event (not supported by unzer-api)!

        :param webhook: The webhook resource to be updated
        :type webhook: Webhook
        :return: The updated webhook
        :rtype: Webhook
        """
        if not isinstance(webhook, Webhook):
            raise TypeError("Expected a Webhook object. Got %r" % type(webhook))
        if not webhook.webhookId:
            raise ValueError("Webhook to update has no id")
        if not webhook.url:
            raise ValueError("Webhook to update has no url")
        data = self.request(
            "webhooks/%s" % webhook.webhookId,
            "PUT",
            {"url": webhook.url},
        )
        return Webhook.fromDict(data)

    def _loadWebhookResponse(self, data):
        """Helper method load webhook responses.

        :param data: The data from the request.
        :type data: dict
        :return: A list of Webhooks
        :rtype: list[Webhook]
        """
        if "events" not in data:
            webhooks = [data]  # got exactly one webhook, data is the webhook itself
        else:
            webhooks = data["events"]  # list of webhooks wrapped in events property
        return [Webhook.fromDict(webhook) for webhook in webhooks]

    def deleteWebhook(self, webhookOrId):
        """Delete a specific webhook.

        :param webhookOrId: A webhook id or webhook model
        :type webhookOrId: str | Webhook
        :return: The id of the deleted webhook
        :type: str
        """
        if isinstance(webhookOrId, Webhook):
            webhookOrId = webhookOrId.webhookId
        data = self.request(
            "webhooks/%s" % webhookOrId,
            "DELETE",
        )
        return data["id"]

    def deleteAllWebhooks(self):
        """Delete all webhooks

        :return: A list of the deleted webhooks
        :rtype: list[dict]
        """
        data = self.request(
            "webhooks",
            "DELETE",
        )
        return data["events"]
