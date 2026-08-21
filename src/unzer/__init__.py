__title__ = "unzer-sdk"
__author__ = "Sven Eberth"
__email__ = "se@mausbrand.de"
__version__ = "1.5.0"

from .client import UnzerClient
from .model import *
from .model import __all__ as _model_all

# UnzerClient is the entry point; everything else is re-exported from .model.
__all__ = ["UnzerClient", *_model_all]
