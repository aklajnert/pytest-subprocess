class ProcessNotRegisteredError(Exception):
    """
    Raised when the attempted command wasn't registered before.
    Use `fake_process.allow_unregistered(True)` if you want to use real subprocess.
    """


class IncorrectProcessDefinition(Exception):
    """Raised when the register() has been called with wrong arguments"""


class PluginInternalError(Exception):
    """Raised in case of an internal error in the plugin"""
