"""
This logging Formatter prints both UTC and local timestamps to the logs
"""
import datetime
from logging import Formatter

import arrow

LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


class LogFormatter(Formatter):
    def usesTime(self):
        return True

    def formatTime(self, record, datefmt=None):
        created_at = arrow.get(record.created)
        created_at_local = arrow.get(record.created).to(LOCAL_TIMEZONE)
        utc_timestamp = created_at.format("YYYY-MM-DDTHH:mm:ss") + "Z"
        local_timestamp = created_at_local.format("YYYY-MM-DDTHH:mm:ssZZ")
        return "[{}] [{}]".format(utc_timestamp, local_timestamp)
