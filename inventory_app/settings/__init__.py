"""Settings package shim

This package exists alongside a legacy module file `inventory_app/settings.py`.
To maintain compatibility, import all UPPERCASE settings from that file so that
`inventory_app.settings` (the package) behaves like the base settings module.
"""

from importlib import util as _util
from pathlib import Path as _Path

_base_path = _Path(__file__).resolve().parent.parent / "settings.py"
_spec = _util.spec_from_file_location("inventory_app._base_settings", str(_base_path))
_mod = _util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec and _spec.loader
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

# Re-export all Django settings-style constants
for _k, _v in _mod.__dict__.items():
    if _k.isupper():
        globals()[_k] = _v

del _util, _Path, _base_path, _spec, _mod, _k, _v
