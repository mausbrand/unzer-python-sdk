# -*- coding: utf-8 -*-

__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

from .abstract_paymenttype import PaymentType


class Card(PaymentType):
    method = "card"
