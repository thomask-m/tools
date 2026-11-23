"""All tasks. Import order here is the default run order.

To add a task: create a module in this package with a `@register`ed Task
subclass, then import it below.
"""
from . import xcode_clt  # noqa: F401
from . import macos_defaults  # noqa: F401
from . import homebrew  # noqa: F401
from . import emacs  # noqa: F401
from . import emacs_config  # noqa: F401
