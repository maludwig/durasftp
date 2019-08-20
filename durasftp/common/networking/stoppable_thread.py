import signal
import threading
from threading import Event, Lock

from durasftp.common.log import get_logger

global_stop_event = Event()
mutex = Lock()
thread_count = 0

logger = get_logger(__name__)


class StoppableThread(threading.Thread):
    """
    Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition.
    """

    def __init__(self):
        super(StoppableThread, self).__init__()
        self.thread_num = get_next_thread_num()
        self.stop_event = threading.Event()

    def stop(self):
        self.before_stop()
        self.stop_event.set()
        self.after_stop()

    def before_stop(self):
        pass

    def after_stop(self):
        pass

    def stopped(self):
        thread_is_stopped = self.stop_event.is_set()
        program_is_stopped = global_stop_event.is_set()
        return thread_is_stopped or program_is_stopped

    def log_info(self, msg):
        logger.info("{}({}) {}".format(type(self).__name__, self.thread_num, msg))

    def log_debug(self, msg):
        logger.debug("{}({}) {}".format(type(self).__name__, self.thread_num, msg))


def stop_all_threads(*args):
    global_stop_event.set()


def get_next_thread_num():
    global thread_count
    with mutex:
        thread_count += 1
        thread_num = thread_count
    return thread_num


signal.signal(signal.SIGTERM, stop_all_threads)
signal.signal(signal.SIGINT, stop_all_threads)
