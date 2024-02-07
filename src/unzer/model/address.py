# -*- coding: utf-8 -*-

__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

from .base import BaseModel


class Address(BaseModel):
    def __init__(
            self,
            firstname,
            lastname,
            street=None,
            state=None,
            zipCode=None,
            city=None,
            country=None,
            **kwargs
    ):
        """Create a new Address.

        :param firstname: (optional) Address firstname (+lastname: max. 81 chars). Required in case of billing address.
        :type firstname: basestring
        :param lastname: (optional)  Address lastname (+firstname: max. 81 chars). Required in case of billing address.
        :type lastname: basestring
        :param street: (optional) Address street (max. 50 chars). Required in case of billing address.
        :type street: basestring
        :param state: (optional) Address state in ISO 3166-2 format (max. 8 chars). Required in case of billing address.
        :type state: basestring
        :param zipCode: (optional) Address zip code (max. 10 chars). Required in case of billing address.
        :type zipCode: basestring
        :param city: (optional) Address city (max. 30 chars). Required in case of billing address.
        :type city: basestring
        :param country: (optional) Address country in ISO A2 format (max. 2 chars). Required in case of billing address.
        :type country: basestring
        """
        self.firstname = firstname  # type: str
        self.lastname = lastname  # type: str
        self.street = street  # type: str
        self.state = state  # type: str
        self.zipCode = zipCode  # type: str
        self.city = city  # type: str
        self.country = country  # type: str

    @property
    def name(self):
        return "%s %s" % (
            self.getString(self.firstname),
            self.getString(self.lastname),
        )

    @name.setter
    def name(self, name):
        try:
            self.firstname, self.lastname = name.split(" ", 1)
        except ValueError:
            self.firstname, self.lastname = name, None

    def serialize(self):
        return {
            "name": self.getString(self.name),
            "street": self.getString(self.street),
            "state": self.getString(self.state),
            "zip": self.getString(self.zipCode),
            "city": self.getString(self.city),
            "country": self.getString(self.country),
        }

    @classmethod
    def fromDict(cls, data):
        try:
            firstname, lastname = data["name"].split(" ", 1)
        except ValueError:
            firstname, lastname = data["name"], None
        return cls(
            firstname=firstname,
            lastname=lastname,
            street=data["street"],
            state=data["state"],
            zipCode=data["zip"],
            city=data["city"],
            country=data["country"],
        )
