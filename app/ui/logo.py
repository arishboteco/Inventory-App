from base64 import b64decode
from pathlib import Path

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
    """Return the sidebar logo bytes.

    If a ``logo.png`` file exists alongside this module, it is used. Otherwise
    the built-in base64-encoded image is returned.
    """
    custom_logo_path = Path(__file__).with_name("logo.png")
    if custom_logo_path.is_file():
        return custom_logo_path.read_bytes()
    return b64decode(LOGO_BASE64)
