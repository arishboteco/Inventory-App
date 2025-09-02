"""Django settings package.

This package defaults to the base settings. Set ``DJANGO_SETTINGS_MODULE``
to ``inventory_app.settings.dev`` or ``inventory_app.settings.prod`` as
needed for each environment.
"""

from .base import *  # noqa

__all__ = [name for name in globals() if name.isupper()]
