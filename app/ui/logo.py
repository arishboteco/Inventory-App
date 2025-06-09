from base64 import b64decode

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
    """Return the decoded logo image bytes."""
    return b64decode(LOGO_BASE64)
