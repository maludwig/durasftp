import logging
from argparse import ArgumentParser
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG
from os import environ

from durasftp.common.log.log_formatter import LogFormatter

NAME_TO_LOG_LEVEL = {
    "CRITICAL": CRITICAL,
    "ERROR": ERROR,
    "WARN": WARNING,
    "WARNING": WARNING,
    "INFO": INFO,
    "DEBUG": DEBUG,
}
FORMAT_STRING = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

log_level_string = environ.get("LOG_LEVEL", "WARNING")
log_level = NAME_TO_LOG_LEVEL[log_level_string]
log_file_path = None
project_logger = logging.getLogger("mamba")
project_handler = logging.StreamHandler()
project_handler.setFormatter(LogFormatter(FORMAT_STRING))
for handler in project_logger.handlers:
    project_logger.removeHandler(handler)
project_logger.addHandler(project_handler)
project_logger.setLevel(log_level)
project_logger.propagate = False


def set_log_level(new_log_level):
    global log_level
    log_level = new_log_level
    project_logger.setLevel(new_log_level)


def get_log_level():
    return log_level


def set_log_file_path(new_log_file_path):
    global log_file_path, project_handler, project_logger
    log_file_path = new_log_file_path
    for handler in project_logger.handlers:
        project_logger.removeHandler(handler)
    project_handler = logging.FileHandler(filename=log_file_path)
    project_handler.setFormatter(LogFormatter(FORMAT_STRING))
    project_logger.addHandler(project_handler)


def get_log_file_path():
    return log_file_path


def set_project_logger(new_project_logger):
    global project_logger
    project_logger = new_project_logger


def get_project_logger():
    return project_logger


def add_logger_args(parser):
    from common.log.log_file_action import LogFileAction
    from common.log.log_level_action import LogLevelAction

    parser.add_argument(
        "-v",
        "--verbose",
        action=LogLevelAction,
        help="Increase log output, specify multiple times for extra output (ex. -vvv)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action=LogLevelAction,
        help="Less log output, -qqq for no logging",
    )
    parser.add_argument("--log-file", action=LogFileAction, help="Path for a log file")


def arg_parser_with_logs():
    parser = ArgumentParser()
    add_logger_args(parser)
    return parser


def get_logger(name):
    return logging.getLogger("mamba." + name)


if __name__ == "__main__":
    parser = arg_parser_with_logs()
    args = parser.parse_args()
    logger = get_logger("common.log")
    logger.critical("critical")
    logger.error("error")
    logger.warning("warning")
    logger.info("info")
    logger.debug("debug")
