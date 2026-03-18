"""Nyx error types."""


class NyxError(Exception):
    """Base error for all Nyx errors."""
    pass


class NyxTimeout(NyxError):
    """Request timed out."""
    pass


class NyxConnectionError(NyxError):
    """Could not connect to the target."""
    pass


class NyxNotFound(NyxError):
    """Element or target not found."""
    pass


class NyxInstallError(NyxError):
    """Browser installation failed."""
    pass


class NyxLaunchError(NyxError):
    """Browser failed to launch."""
    pass


class NyxBrowserCrashed(NyxError):
    """Browser process exited unexpectedly."""
    pass
