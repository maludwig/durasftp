#!/usr/bin/env python

import socket
from argparse import ArgumentParser
from time import sleep

import docker
import paramiko
from docker.errors import NotFound
from paramiko.packet import Packetizer

from durasftp.common.log import get_logger, add_logger_args
from test.common.config import SFTP_PASS, SFTP_PORT, SFTP_USER, SFTP_HOST, SFTP_MOUNT

CONTAINER_NAME = "test_sftp"
MAX_ATTEMPTS = 50

logger = get_logger(__name__)

client = docker.from_env()


def ssh_is_up():
    logger.debug("Attempting to use basic connection")
    try:
        with socket.create_connection((SFTP_HOST, SFTP_PORT), 2) as sock:
            packetizer = Packetizer(sock)
            line = packetizer.readline(5)
            if "SSH-" in line:
                logger.debug("Basic connection established")
                return True
            else:
                logger.debug("Basic connection established but no SSH Headers found")
    except EOFError:
        logger.debug("Basic connection established but no lines read")
    except ConnectionRefusedError:
        logger.debug("Basic connection could not be established yet")
    return False


def server_is_up():
    logger.debug("Attempting to connect")
    try:
        if ssh_is_up():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS)
            logger.info("Connected!")
            ssh.close()
            return True
    except paramiko.ssh_exception.SSHException as ex:
        logger.debug("Container was not ready")
    return False


def remove_container():
    try:
        svr = client.containers.get(CONTAINER_NAME)
        if svr.status == "running":
            svr.kill()
        svr.remove()
    except NotFound:
        pass


def kill_container():
    try:
        svr = client.containers.get(CONTAINER_NAME)
        if svr.status == "running":
            svr.kill()
    except NotFound:
        pass


def start_container():
    svr = client.containers.run(
        "atmoz/sftp",
        "{}:{}:::".format(SFTP_USER, SFTP_PASS),
        ports={"22": SFTP_PORT},
        volumes={SFTP_MOUNT: {"bind": "/home", "mode": "rw"}},
        detach=True,
        name=CONTAINER_NAME,
    )
    for attempt_num in range(MAX_ATTEMPTS):
        sleep(0.1)
        if server_is_up():
            break
        else:
            if attempt_num == MAX_ATTEMPTS - 1:
                raise Exception(
                    "Timed out connecting to sftp://{}:{}/".format(SFTP_HOST, SFTP_PORT)
                )
    return svr


def restart_container():
    remove_container()
    return start_container()


def get_container():
    try:
        svr = client.containers.get(CONTAINER_NAME)
        if svr.status == "running":
            return svr
        else:
            return restart_container()
    except NotFound:
        return start_container()


if __name__ == "__main__":
    parser = ArgumentParser()
    add_logger_args(parser)
    args = parser.parse_args()
    logger.info("Starting SFTP Server container")
    svr = restart_container()
    if svr:
        logger.info("SFTP Server container is running")
    else:
        logger.debug("FAILED TO START")
