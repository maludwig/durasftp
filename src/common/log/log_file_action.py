import argparse
from common.log import set_log_file_path


class LogFileAction(argparse.Action):
    def __init__(self, option_strings, dest, default=None, required=False, help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=1,
            default=default,
            required=required,
            help=help,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        log_file_path = values[0]
        if log_file_path is not None:
            set_log_file_path(log_file_path)
        setattr(namespace, self.dest, log_file_path)
