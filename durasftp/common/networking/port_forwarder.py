#!/usr/bin/env python

import random
import socket
from threading import Event
from time import sleep

from durasftp.common import ONE_KB
from durasftp.common.log import arg_parser_with_logs, get_logger
from durasftp.common.networking import INFINTE_SPEED
from durasftp.common.networking.stoppable_thread import StoppableThread

all_threads = []

logger = get_logger(__name__)


class ListeningThread(StoppableThread):
    def __init__(
        self,
        local_port,
        dest_host,
        dest_port,
        kbps=INFINTE_SPEED,
        packet_drop_rate=0,
        connecting_lag=0,
    ):
        super().__init__()
        self.local_port = local_port
        self.dest_host = dest_host
        self.dest_port = dest_port
        self.count = 0
        self.kbps = kbps
        self.packet_drop_rate = packet_drop_rate
        self.connecting_lag = connecting_lag
        self.forwarding_threads = []
        self.is_listening = Event()

    def after_stop(self):
        for forwarding_thread in self.forwarding_threads:
            forwarding_thread.stop()
        for forwarding_thread in self.forwarding_threads:
            forwarding_thread.join()

    def run(self):
        self.log_info(
            "Listening on {}, forwarding to {}:{}".format(
                self.local_port, self.dest_host, self.dest_port
            )
        )
        self.log_debug(
            "Still listening on {}, forwarding to {}:{}".format(
                self.local_port, self.dest_host, self.dest_port
            )
        )
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
                self.log_debug(
                    "Still accepting on {}, forwarding to {}:{}".format(
                        self.local_port, self.dest_host, self.dest_port
                    )
                )
                client_socket = dock_socket.accept()[0]
                client_socket.settimeout(1)
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.settimeout(1)
                server_socket.connect((self.dest_host, self.dest_port))
                sleep(self.connecting_lag)
                self.log_debug("Taking mutex")
                client_to_server_forwarding_thread = ForwardingThread(
                    client_socket, server_socket, self.kbps, self.packet_drop_rate
                )
                server_to_client_forwarding_thread = ForwardingThread(
                    server_socket, client_socket, self.kbps, self.packet_drop_rate
                )
                all_threads.append(client_to_server_forwarding_thread)
                all_threads.append(server_to_client_forwarding_thread)
                client_to_server_forwarding_thread.start()
                server_to_client_forwarding_thread.start()
                self.forwarding_threads.append(client_to_server_forwarding_thread)
                self.forwarding_threads.append(server_to_client_forwarding_thread)
                self.log_debug("Releasing mutex")
            except socket.timeout:
                self.log_debug("Timed out waiting for a connection")

        try:
            self.log_info("Closing S:{}".format(dock_socket.fileno()))
            dock_socket.close()
            self.log_info("Closed S:{}".format(dock_socket.fileno()))
        except OSError:
            self.log_info("Error Closing S:{}".format(dock_socket.fileno()))
        self.log_info("We are stopping")

    def adjust_kbps(self, kbps, adjust_future_connections=True):
        if adjust_future_connections:
            self.kbps = kbps
        for forwarding_thread in self.forwarding_threads:
            forwarding_thread.adjust_kbps(kbps)


class ForwardingThread(StoppableThread):
    def __init__(
        self, server_socket, client_socket, kbps=INFINTE_SPEED, packet_drop_rate=0
    ):
        super().__init__()
        self.server_socket = server_socket
        self.client_socket = client_socket
        self.packet_drop_rate = packet_drop_rate
        self.adjust_kbps(kbps)
        self.kbps = kbps
        self.seconds_between_packets = 0.1
        self.packet_size = ONE_KB * 64
        self.adjust_kbps(kbps)

    def randomly_drop_packet(self):
        if self.packet_drop_rate == 0:
            return False
        elif random.uniform(0, 1) < self.packet_drop_rate:
            return True
        else:
            return False

    def adjust_kbps(self, kbps):
        self.kbps = kbps
        if kbps == INFINTE_SPEED or kbps == 0:
            self.packet_size = ONE_KB * 64
        else:
            self.packet_size = int(ONE_KB * (kbps / 10))

    def run(self):
        self.log_info(
            "Forwarding a connection with S:{} and C:{}".format(
                self.server_socket.fileno(), self.client_socket.fileno()
            )
        )
        bytes_received = b" "
        try:
            while (
                self.stopped() is False
                and bytes_received
                and self.server_socket.fileno() != -1
            ):
                self.log_debug("Not stopped and socket is connected")
                try:
                    bytes_received = self.client_socket.recv(self.packet_size)
                    if bytes_received:
                        if self.kbps != 0:
                            if self.kbps != INFINTE_SPEED:
                                sleep(self.seconds_between_packets)
                            if not self.randomly_drop_packet():
                                self.log_debug(
                                    "Sending string: {}".format(bytes_received)
                                )
                                self.server_socket.sendall(bytes_received)
                            else:
                                self.log_debug("Randomly dropped packet")
                except socket.timeout as e:
                    self.log_debug("Timed out awaiting data")
                    bytes_received = b" "
                except BrokenPipeError:
                    self.log_debug("Pipe broke")
                except ConnectionResetError:
                    self.log_debug("Connection was reset")
                except OSError as ex:
                    msg = str(ex)
                    if msg == "Bad file descriptor":
                        # The other half is dead
                        self.stop()
        finally:
            self.log_info("Closing C:{}".format(self.client_socket.fileno()))
            self.client_socket.close()
            self.log_info("Closed C:{}".format(self.client_socket.fileno()))
            if self.stopped():
                self.log_info("Stopped")
            else:
                self.log_info("Connection closed naturally")


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
