"""Dynamic settings loader.

When ``DJANGO_SETTINGS_MODULE`` points at ``inventory_app.settings`` this
module selects the appropriate environment submodule based on the
``DJANGO_ENV`` environment variable (defaulting to ``dev``). If
``DJANGO_SETTINGS_MODULE`` is already set to a specific submodule like
``inventory_app.settings.test``, this loader does nothing so the submodule
can handle configuration itself.
"""

from importlib import import_module

from core.config import settings as app_settings

if app_settings.django_settings_module == "inventory_app.settings":
    DJANGO_ENV = app_settings.django_env
    _module = import_module(f"inventory_app.settings.{DJANGO_ENV}")

    for setting in dir(_module):
        if setting.isupper():
            globals()[setting] = getattr(_module, setting)

    __all__ = [s for s in globals() if s.isupper()]
else:
    __all__: list[str] = []
