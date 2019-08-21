import socket

import paramiko
import pysftp
from paramiko import SSHException
from pysftp import ConnectionException

from durasftp.common.log import get_logger

logger = get_logger(__name__)


def retry_on_fail(fn):
    def wrapper(self, *args, **kwargs):
        for attempt_num in range(self.max_attempts):
            try:
                logger.info("Running {}()".format(fn.__name__))
                return fn(self, *args, **kwargs)
            except (
                AttributeError,
                SSHException,
                ConnectionRefusedError,
                socket.gaierror,
                socket.timeout,
            ) as ex:
                logger.warning(ex)
                if attempt_num == self.max_attempts - 1:
                    logger.error(
                        "Failed {}(), attempt {} of {}".format(
                            fn.__name__, attempt_num, self.max_attempts
                        )
                    )
                    raise ex
                else:
                    logger.warning(
                        "Retrying {}(), attempt {} of {}".format(
                            fn.__name__, attempt_num, self.max_attempts
                        )
                    )
                    self.reconnect()

    return wrapper


class DurableSFTPConnection(pysftp.Connection):
    def __init__(
        self,
        host,
        username=None,
        private_key=None,
        password=None,
        port=22,
        private_key_pass=None,
        ciphers=None,
        log=False,
        cnopts=None,
        default_path=None,
        timeout=15,
        max_attempts=3,
    ):
        logger.debug("New SFTPConnection for sftp://{}:{}".format(host, port))
        self._timeout = timeout
        self._sock = None
        self.max_attempts = max_attempts
        self.host = host
        self.port = port
        self.password = password
        self.private_key = private_key
        self.private_key_pass = private_key_pass
        super().__init__(
            host,
            username,
            private_key,
            password,
            port,
            private_key_pass,
            ciphers,
            log,
            cnopts,
            default_path,
        )
        self.timeout = self._timeout

    def _start_transport(self, host, port):
        """start the transport and set the ciphers if specified."""

        try:
            self._sock = socket.create_connection((host, port), self._timeout)
            self._transport = paramiko.Transport(self._sock)
            # Set security ciphers if set
            if self._cnopts.ciphers is not None:
                ciphers = self._cnopts.ciphers
                self._transport.get_security_options().ciphers = ciphers
        except (
            AttributeError,
            SSHException,
            ConnectionRefusedError,
            socket.gaierror,
            socket.timeout,
        ) as ex:
            # couldn't connect
            logger.critical(ex)
            if isinstance(self._sock, socket.socket):
                self._sock.close()
            raise ConnectionException(host, port)

    def reconnect(self):
        logger.warning("Reconnecting sftp://{}:{}".format(self.host, self.port))
        # Begin the SSH transport.
        self.close()
        self._transport = None
        self._start_transport(self.host, self.port)
        self._transport.use_compression(self._cnopts.compression)
        self._set_authentication(self.password, self.private_key, self.private_key_pass)
        self._transport.connect(**self._tconnect)
        self._sftp_connect()
        self.timeout = self._timeout

    @retry_on_fail
    def pwd(self):
        return super().pwd()

    @retry_on_fail
    def get(self, remotepath, localpath=None, callback=None, preserve_mtime=False):
        return super().get(remotepath, localpath, callback, preserve_mtime)

    @retry_on_fail
    def get_d(self, remotedir, localdir, preserve_mtime=False):
        return super().get_d(remotedir, localdir, preserve_mtime)

    @retry_on_fail
    def get_r(self, remotedir, localdir, preserve_mtime=False):
        return super().get_r(remotedir, localdir, preserve_mtime)

    @retry_on_fail
    def getfo(self, remotepath, flo, callback=None):
        return super().getfo(remotepath, flo, callback)

    @retry_on_fail
    def put(
        self,
        localpath,
        remotepath=None,
        callback=None,
        confirm=True,
        preserve_mtime=False,
    ):
        return super().put(localpath, remotepath, callback, confirm, preserve_mtime)

    @retry_on_fail
    def put_d(self, localpath, remotepath, confirm=True, preserve_mtime=False):
        return super().put_d(localpath, remotepath, confirm, preserve_mtime)

    @retry_on_fail
    def put_r(self, localpath, remotepath, confirm=True, preserve_mtime=False):
        return super().put_r(localpath, remotepath, confirm, preserve_mtime)

    @retry_on_fail
    def putfo(self, flo, remotepath=None, file_size=0, callback=None, confirm=True):
        return super().putfo(flo, remotepath, file_size, callback, confirm)

    @retry_on_fail
    def execute(self, command):
        return super().execute(command)

    @retry_on_fail
    def cd(self, remotepath=None):
        return super().cd(remotepath)

    @retry_on_fail
    def chdir(self, remotepath):
        return super().chdir(remotepath)

    @retry_on_fail
    def chmod(self, remotepath, mode=777):
        return super().chmod(remotepath, mode)

    @retry_on_fail
    def chown(self, remotepath, uid=None, gid=None):
        return super().chown(remotepath, uid, gid)

    @retry_on_fail
    def getcwd(self):
        return super().getcwd()

    @retry_on_fail
    def listdir(self, remotepath="."):
        return super().listdir(remotepath)

    @retry_on_fail
    def listdir_attr(self, remotepath="."):
        return super().listdir_attr(remotepath)

    @retry_on_fail
    def mkdir(self, remotepath, mode=777):
        return super().mkdir(remotepath, mode)

    @retry_on_fail
    def normalize(self, remotepath):
        return super().normalize(remotepath)

    @retry_on_fail
    def isdir(self, remotepath):
        return super().isdir(remotepath)

    @retry_on_fail
    def isfile(self, remotepath):
        return super().isfile(remotepath)

    @retry_on_fail
    def makedirs(self, remotedir, mode=777):
        return super().makedirs(remotedir, mode)

    @retry_on_fail
    def readlink(self, remotelink):
        return super().readlink(remotelink)

    @retry_on_fail
    def remove(self, remotefile):
        return super().remove(remotefile)

    @retry_on_fail
    def rmdir(self, remotepath):
        return super().rmdir(remotepath)

    @retry_on_fail
    def rename(self, remote_src, remote_dest):
        return super().rename(remote_src, remote_dest)

    @retry_on_fail
    def stat(self, remotepath):
        return super().stat(remotepath)

    @retry_on_fail
    def lstat(self, remotepath):
        return super().lstat(remotepath)

    @retry_on_fail
    def close(self):
        return super().close()

    @retry_on_fail
    def open(self, remote_file, mode="r", bufsize=-1):
        return super().open(remote_file, mode, bufsize)

    @retry_on_fail
    def exists(self, remotepath):
        return super().exists(remotepath)

    @retry_on_fail
    def lexists(self, remotepath):
        return super().lexists(remotepath)

    @retry_on_fail
    def symlink(self, remote_src, remote_dest):
        return super().symlink(remote_src, remote_dest)

    @retry_on_fail
    def truncate(self, remotepath, size):
        return super().truncate(remotepath, size)

    @retry_on_fail
    def walktree(self, remotepath, fcallback, dcallback, ucallback, recurse=True):
        return super().walktree(remotepath, fcallback, dcallback, ucallback, recurse)

    @retry_on_fail
    def sftp_client(self):
        return super().sftp_client()

    @retry_on_fail
    def active_ciphers(self):
        return super().active_ciphers()

    @retry_on_fail
    def active_compression(self):
        return super().active_compression()

    @retry_on_fail
    def security_options(self):
        return super().security_options()

    @retry_on_fail
    def logfile(self):
        return super().logfile()

    @retry_on_fail
    def remote_server_key(self):
        return super().remote_server_key()
