"""
Handles file transfer via `cp`
"""

import logging
from typing import TYPE_CHECKING, Any, Union

from alchemy_test.transport.transport import Transport

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.connection.url import URL

logger = logging.getLogger(__name__)


class cp(Transport):

    def __init__(self, url: Union[URL, None], *args: Any, **kwargs: Any):
        super().__init__(url=url, *args, **kwargs)

        logger.info("created new cp transport")

    def cmd(self, primary: str, secondary: str) -> str:
        cmd = "mkdir -p {secondary} ; cp -r --preserve {primary} {secondary}"
        base = cmd.format(primary=primary, secondary=secondary)
        logger.debug(f'returning formatted cmd: "{base}"')
        return base
