import argparse
import logging

from durasftp.common.log import set_log_level


class LogLevelAction(argparse.Action):
    """
    This argparse action allows for a command line argument to specify the log level
    Examples:
        Silent (no logging):
            python <script> -qqq
        Critical errors only:
            python <script> -qq
        All Errors:
            python <script> -q
        Warnings, and all errors (default):
            python <script>
        Information, warnings, and errors:
            python <script> -v
        Debug logging:
            python <script> -vv
    """

    def __init__(self, option_strings, dest, default=None, required=False, help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        global log_level
        count = getattr(namespace, "log_level", None)
        if count is None:
            count = 0
        if self.dest == "verbose":
            count += 1
        elif self.dest == "quiet":
            count -= 1

        if count == -3:
            # Silent
            log_level = logging.CRITICAL + 10
        elif count == -2:
            log_level = logging.CRITICAL
        elif count == -1:
            log_level = logging.ERROR
        elif count == 0:
            log_level = logging.WARNING
        elif count == 1:
            log_level = logging.INFO
        elif count == 2:
            log_level = logging.DEBUG
        setattr(namespace, "log_level", count)
        set_log_level(log_level)
