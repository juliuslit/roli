"""The one exception type the service turns into an ``ErrorResult``."""

from __future__ import annotations


class RoliNutritionError(Exception):
    """A failure with one of the nine error codes from spec section 9.

    ``message`` is fixed text owned by this library. It never contains the API
    key, request headers, USDA's raw text, a URL or a stack trace.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
