import socket
from threading import Event

from durasftp.common import ONE_KB
from durasftp.common.log import arg_parser_with_logs, get_logger
from durasftp.common.networking.stoppable_thread import StoppableThread

all_threads = []

logger = get_logger(__name__)

INFINTE_SPEED = -1
ANY_RANDOM_AVAILABLE_PORT = 0


class EchoThread(StoppableThread):
    def __init__(self, thread_num, connected_socket):
        super().__init__(thread_num)
        self.connected_socket = connected_socket
        self.packet_size = ONE_KB

    def run(self):
        self.log_info(
            "Echoing a connection with C:{}".format(self.connected_socket.fileno())
        )
        bytes_received = b" "
        try:
            while self.stopped() is False and bytes_received:
                self.log_debug("Not stopped and socket is connected")
                try:
                    bytes_received = self.connected_socket.recv(self.packet_size)
                    if bytes_received:
                        self.log_debug("Sending string: {}".format(bytes_received))
                        self.connected_socket.sendall(bytes_received)
                except socket.timeout:
                    self.log_debug("Timed out awaiting data")
                    bytes_received = b" "
                except BrokenPipeError:
                    self.log_debug("Pipe broke")
                except ConnectionResetError:
                    self.log_debug("Connection was reset")
                except OSError as ex:
                    self.log_debug("OSError: {}".format(ex))
                    self.stop()
        finally:
            self.log_info("Closing C:{}".format(self.connected_socket.fileno()))
            self.connected_socket.close()
            self.log_info("Closed C:{}".format(self.connected_socket.fileno()))
            if self.stopped():
                self.log_info("Stopped")
            else:
                self.log_info("Connection closed naturally")


class EchoListeningThread(StoppableThread):
    def __init__(self, local_port=ANY_RANDOM_AVAILABLE_PORT):
        super().__init__()
        self.local_port = local_port
        self.connected_threads = []
        self.is_listening = Event()

    def after_stop(self):
        for connected_thread in self.connected_threads:
            connected_thread.stop()
        for connected_thread in self.connected_threads:
            connected_thread.join()

    def run(self):
        dock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dock_socket.settimeout(1)
        try:
            host = socket.gethostbyname(socket.gethostname())
            dock_socket.bind((host, self.local_port))
        except OSError as ex:
            raise OSError("ERROR: {}, Port: {}".format(str(ex), self.local_port))
        dock_socket.listen(5)
        self.local_port = dock_socket.getsockname()[1]
        self.log_info(
            "Listening on {} with D:{}".format(self.local_port, dock_socket.fileno())
        )
        self.is_listening.set()
        while self.stopped() is False:
            try:
                self.log_debug("Still accepting on {}".format(self.local_port))
                connected_socket = dock_socket.accept()[0]
                connected_socket.settimeout(1)
                self.log_debug("Taking mutex")
                echo_thread = EchoThread(connected_socket)
                self.connected_threads.append(echo_thread)
                echo_thread.start()
            except socket.timeout:
                self.log_debug("Timed out waiting for a connection")

        try:
            self.log_info("Closing S:{}".format(dock_socket.fileno()))
            dock_socket.close()
            self.log_info("Closed S:{}".format(dock_socket.fileno()))
        except OSError:
            self.log_info("Error Closing S:{}".format(dock_socket.fileno()))
        self.log_info("We are stopping")


def stop_all_threads(*args):
    global all_threads
    logger.info("Global stop signal received")
    for one_thread in all_threads:
        one_thread.stop()
        one_thread.join()
        all_threads = []
    logger.info("All threads stopped")


def start_forwarding(
    local_port,
    remote_host,
    remote_port,
    kbps=INFINTE_SPEED,
    packet_drop_rate=0,
    connecting_lag=0,
):
    listening_thread = ListeningThread(
        local_port, remote_host, remote_port, kbps, packet_drop_rate, connecting_lag
    )
    all_threads.append(listening_thread)
    listening_thread.start()
    listening_thread.is_listening.wait(2)
    return listening_thread


def stop_forwarding():
    stop_all_threads()


if __name__ == "__main__":
    parser = arg_parser_with_logs()
    parser.add_argument("local_port", type=int, help="The local port to open")
    parser.add_argument("remote_host", type=str, help="The remote host to forward to")
    parser.add_argument("remote_port", type=int, help="The remote port to connect to")
    parser.add_argument(
        "--packet-drop-rate",
        default=0,
        type=float,
        help="What fraction of packets to drop (ex. 0.2 will drop one in five packets)",
    )
    parser.add_argument(
        "--kbps",
        default=INFINTE_SPEED,
        type=float,
        help="The maximum speed to forward packets at",
    )
    parser.add_argument(
        "--connecting-lag",
        default=0,
        type=float,
        help="The amount of seconds to wait before actually connecting",
    )
    args = parser.parse_args()
    listener_thread = start_forwarding(
        args.local_port,
        args.remote_host,
        args.remote_port,
        args.kbps,
        args.packet_drop_rate,
        args.connecting_lag,
    )
    listener_thread.join()
