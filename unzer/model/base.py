# -*- coding: utf-8 -*-

__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"

import abc


class BaseModel(object):
    __metaclass__ = abc.ABCMeta

    EMPTY_STRING = ""

    REQUIRED_ATTRIBUTES = []

    def getString(self, value):
        if value is None:
            return self.EMPTY_STRING
        return value

    @abc.abstractmethod
    def serialize(self):
        """Serialize data from an object as dict for the request-payload."""
        pass

    @classmethod
    @abc.abstractmethod
    def fromDict(cls, data):
        """Unserialize data from a dict from a response to new object"""
        pass

    def validateBeforeRequest(self):
        """Validate the model.

        Useful to check the model for validity before the API request.
        By default check for the required attributes,
        set in :attr:`REQUIRED_ATTRIBUTES` (class attribute).
        """
        for attr in type(self).REQUIRED_ATTRIBUTES:  # use always the cls-attributes
            if not getattr(self, attr):
                raise ValueError("%s misses the attribute *%s*." % (type(self).__name__, attr))
        return True

    def __repr__(self):
        return "%s.%s(%s)" % (
            self.__class__.__module__,
            self.__class__.__name__,
            ", ".join("%s=%r" % (k, v) for k, v in sorted(self))
        )

    def asDict(self):
        """Return the model as dict.

        This will not be done recursive.
        """
        # instance attributes
        data = {k: v for k, v in vars(self).items() if not k.startswith("_")}
        # class properties
        for k, v in vars(self.__class__).items():
            if isinstance(v, property):
                data[k] = getattr(self, k)
        return data

    def __iter__(self):
        """Yield the attributes of the model"""
        for k, v in self.asDict().items():
            yield k, v
