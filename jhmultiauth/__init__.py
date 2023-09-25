"""
Allows multiple JupyterHub authenticators to be used at the same time.
"""

from .jhmultiauth import MultiAuthenticator

__version__ = "0.1.0"
__all__ = ["MultiAuthenticator"]