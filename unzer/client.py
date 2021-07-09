# -*- coding: utf-8 -*-

__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

import logging
import time
from types import NoneType

import requests
from urllib3.exceptions import TimeoutError

from . import __version__
from .model import *
from .model.basket import Basket
from .model.payment import PaymentGetResponse, PaymentResponse
from .model.paymentpage import PaymentPage, PaymentPageResponse
from .model.webhook import Webhook

logger = logging.getLogger("unzer-sdk")


class UnzerClient(object):
	endpoint = "https://api.unzer.com/v1"
	retryDelays = (1, 2, 4, 8)
	timeout = 5

	def __init__(
			self,
			privateKey,
			publicKey,
			sandbox=False,
			language="en",
	):
		super(UnzerClient, self).__init__()
		self.privateKey = privateKey
		self.publicKey = publicKey
		self.sandbox = sandbox
		self.language = language

	def request(self, operation, method, payload=None):
		"""Perform a request to the unzer-api.

		This method does not really perform the request itself,
		but rather prepares the request for :meth:`_request`.

		:param operation: The HTTP method (e.g. POST, GET).
		:param method: The method on the REST API. (path).
		:param payload: The payload for this request.
			Send json-encoded as body.
		:return: The json-decoded response from the api.
		:rtype: Any
		"""
		url = "%s/%s" % (self.endpoint, operation)
		headers = {
			"user-agent": "unzer-python-sdk %s" % __version__,
			"content-type": "application/json; charset=UTF-8",
			"accept": "application/json",
			"accept-language": self.language,  # language for translation of customerMessage in errors
		}
		return self._request(
			url,
			method,
			headers,
			payload,
			auth=(self.privateKey, "")
		)

	def _request(self, url, method, headers, payload, auth):
		"""Helper method to perform the request with throttling.

		:param url: The complete URL.
		:type url: str
		:param method: The HTTP method (e.g. POST, GET).
		:type method: str
		:param headers: The HTTP headers.
		:type headers: list[tuple] | dict[str, str]
		:param payload: The HTTP payload (will be json encoded).
		:type url: Any
		:param auth: The authentication for this request.
		:type auth: tuple(str, str)
		:return: The json decoded response
		:type: Any

		:raises: :exc:`ErrorResponse` in case of an client error
			or after last retry failed.
		"""
		r = None
		for idx, delay in enumerate((0,) + self.retryDelays):
			logger.debug("Perform try no. %d (delay: %d)", idx, delay)
			time.sleep(delay)
			logger.debug("%s %s", method, url)
			logger.debug("payload: %r", payload)
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
			except TimeoutError:
				logger.exception("Caught TimeoutError")
				continue
			if 200 <= r.status_code <= 201:
				logger.debug("Response[%s %s]: %r", r.status_code, r.reason, r.json())
				return r.json()
			elif 500 <= r.status_code < 600:
				logger.debug("Server error")
				logger.debug("Response[%s %s]: %r", r.status_code, r.reason, r.text)
				continue
			else:
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

	def getKeyPair(self):
		"""Provides the public key of the used private key as well as a list of the payment types available for the merchant.

		:return: The fetched KeyPairResponse
		:rtype: dict
		"""
		# ToDo: implement KeyPairResponse-model
		return self.request(
			"keypair",
			"GET",
		)

	def getError(self, errorId):
		"""Get information about an error

		:param errorId: The error id (e.g. p-err-abcdefghij1234567rstuvwyxyz)
		:type errorId: str
		:rtype: dict
		"""
		if not isinstance(errorId, basestring):
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
		elif isinstance(customer, basestring):
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
		)
		return self.getBasket(data["id"])

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
		)
		return self.getBasket(data["id"])

	def getBasket(self, basketId):
		"""Fetch a basket.

		:param basketId: basket's id (key)
		:type basketId: str
		:return: The fetched basket object
		:rtype: Basket
		"""
		data = self.request(
			"baskets/%s" % basketId,
			"GET",
		)
		return Basket.fromDict(data)

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
			"paypage/%s" % paymentPage.action,
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
		if not isinstance(payPageId, basestring):
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
		if not isinstance(codeOrOrderId, basestring):
			raise TypeError("Expected a codeOrOrderId of type str. Got %r" % type(codeOrOrderId))
		data = self.request(
			"payments/%s" % codeOrOrderId,
			"GET",
		)
		return PaymentGetResponse.fromDict(data, self)

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
		if not isinstance(codeOrOrderId, basestring):
			raise TypeError("Expected a codeOrOrderId of type str. Got %r" % type(codeOrOrderId))
		if not isinstance(txnCode, (basestring, NoneType)):
			raise TypeError("Expected a txnCode of type str or None. Got %r" % type(txnCode))
		data = self.request(
			"payments/%s/charges/%s" % (codeOrOrderId, txnCode or ""),
			"GET",
		)
		return PaymentResponse.fromDict(data)

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
		return map(Webhook.fromDict, webhooks)

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
