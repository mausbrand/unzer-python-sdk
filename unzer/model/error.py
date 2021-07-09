# -*- coding: utf-8 -*-

__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

import datetime

import requests


class Error(object):
	def __init__(self, code, merchantMessage, customerMessage):
		self.code = code
		self.merchantMessage = merchantMessage
		self.customerMessage = customerMessage

	def __str__(self):
		return "%s %s: %s" % (self.__class__.__name__, self.code, self.merchantMessage)

	def __repr__(self):
		return "%s.%s(code=%r, merchantMessage=%r, customerMessage=%r)" % (
			self.__class__.__module__,
			self.__class__.__name__,
			self.code,
			self.merchantMessage,
			self.customerMessage,
		)


class ErrorResponse(Exception):
	def __init__(
			self,
			message,
			timestamp=None,
			url=None,
			errors=None,
			errorId=None,
			statusCode=0,
			traceId=None,
			isError=None,
			isPending=None,
			isSuccess=None,
			srcResponse=None,

	):
		super(ErrorResponse, self).__init__(message)
		if errors is None:
			errors = []
		self.timestamp = timestamp  # type: str
		self.url = url  # type: str
		self.errors = errors  # type: list[Error]
		self.errorId = errorId  # type: str
		self.statusCode = statusCode  # type: int
		self.traceId = traceId  # type: str
		self.isError = isError  # type: bool
		self.isPending = isPending  # type: bool
		self.isSuccess = isSuccess  # type: bool
		self.srcResponse = srcResponse  # type: requests.Response

	@classmethod
	def fromDict(cls, data, message="Unzer Error"):
		return cls(
			message,
			timestamp=datetime.datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S"),
			url=data["url"],
			errors=[Error(**error) for error in data["errors"]],
			errorId=data["id"],
			traceId=data.get("traceId"),
			isError=data.get("isError"),
			isPending=data.get("isPending"),
			isSuccess=data.get("isSuccess"),
		)

	def __repr__(self):
		return "%s.%s(url=%r, errorId=%r, traceId=%r, errors=%r)" % (
			self.__class__.__module__,
			self.__class__.__name__,
			self.url,
			self.errorId,
			self.traceId,
			self.errors,
		)
