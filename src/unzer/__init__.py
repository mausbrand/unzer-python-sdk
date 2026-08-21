"""An unofficial Python SDK for the Unzer payment API.

Start at :class:`unzer.UnzerClient`; the resource models live in
:mod:`unzer.model` and are re-exported here.

Unzer's documentation and its official SDKs are both wrong often enough that
neither can be treated as authoritative -- where this SDK deviates from them,
the docstring says so and why.
"""
__title__ = "unzer-sdk"
__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"
__version__ = "1.5.0"

from .client import UnzerClient
from .model import *
from .model import __all__ as _model_all

# UnzerClient is the entry point; everything else is re-exported from .model.
__all__ = ["UnzerClient", *_model_all]
