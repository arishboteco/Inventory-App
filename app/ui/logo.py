"""Utilities for loading the sidebar logo.

If a ``logo.png`` file is present in the same directory as this module,
its bytes will be loaded at runtime. Otherwise the fallback base64
string below is decoded.
"""

from base64 import b64decode
from pathlib import Path

# Path to an optional logo image file that can override the embedded base64
LOGO_PATH = Path(__file__).with_name("logo.png")

# Base64-encoded PNG image used for the sidebar logo. Encoding the logo avoids
# committing binary data so pull requests remain text-only.
LOGO_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAAA6UlEQVR4nO3QQQ3AIADAQMAe/vWAhfVF"
    "ltwpaDrP3oNv1uuAPzErMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCsw"
    "KzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCsw"
    "KzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCswKzArMCsw"
    "KzArMCswKzArMCswKzArMCswKzArMCswKzArMCu4caoCXTSYot4AAAAASUVORK5CYII="
)


def get_logo_bytes() -> bytes:
    """Return the sidebar logo image bytes.

    If ``logo.png`` exists next to this file, its contents are returned.
    Otherwise ``LOGO_BASE64`` is decoded.
    """
    if LOGO_PATH.exists():
        return LOGO_PATH.read_bytes()

    return b64decode(LOGO_BASE64)
