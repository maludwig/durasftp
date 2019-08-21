from collections import OrderedDict
from os import makedirs, remove
from shutil import rmtree
from stat import S_ISDIR, S_ISREG

from durasftp.common.log import get_logger
from durasftp.common.sftp.action_codes import SFTPActionCodes

logger = get_logger(__name__)


class SFTPAction:
    def __init__(
        self,
        mirrorer,
        action_code,
        remote_path,
        local_entry=None,
        remote_entry=None,
        **kwargs
    ):
        self.mirrorer = mirrorer
        self.action_code = action_code
        self.remote_path = remote_path
        self.local_path = mirrorer.local_path_from_remote(remote_path)
        self.kwargs = kwargs
        self.handlers = {
            SFTPActionCodes.OK: self.run_ok,
            SFTPActionCodes.LMKDIR: self.run_lmkdir,
            SFTPActionCodes.GET: self.run_get,
            SFTPActionCodes.RMKDIR: self.run_rmkdir,
            SFTPActionCodes.PUT: self.run_put,
        }
        if local_entry is None:
            self.local_entry = None
            self.local_is_dir = False
            self.local_is_file = False
            self.local_exists = False
        else:
            self.local_entry = local_entry
            self.local_is_dir = local_entry.is_dir()
            self.local_is_file = local_entry.is_file()
            self.local_exists = True

        if remote_entry is None:
            self.remote_entry = None
            self.remote_is_dir = False
            self.remote_is_file = False
            self.remote_exists = False
        else:
            self.remote_entry = remote_entry
            self.remote_is_dir = S_ISDIR(self.remote_entry.st_mode)
            self.remote_is_file = S_ISREG(self.remote_entry.st_mode)
            self.remote_exists = True

    def run(self, callback=None, dry_run=False):
        logger.info("Running: {}".format(self.__repr__()))
        self.handlers[self.action_code](dry_run)
        logger.info("Ran: {}".format(self.__repr__()))
        if callback is not None:
            logger.info("Running CB for: {}".format(self.__repr__()))
            callback(self)
            logger.info("Ran CB for: {}".format(self.__repr__()))

    def run_ok(self, dry_run):
        logger.debug("OK: {}".format(self.remote_path))

    def run_lmkdir(self, dry_run):
        if self.local_is_file:
            logger.info("Removing: {}".format(self.local_path))
            if not dry_run:
                remove(self.local_path)
        logger.info("Making directory: {}".format(self.local_path))
        if not dry_run:
            makedirs(self.local_path, exist_ok=True)

    def run_get(self, dry_run):
        logger.info("run_get: {}".format(self.remote_path))
        if self.local_is_file:
            logger.info("Removing: {}".format(self.local_path))
            if not dry_run:
                remove(self.local_path)
        elif self.local_is_dir:
            logger.info("Removing Directory: {}".format(self.local_path))
            if not dry_run:
                rmtree(self.local_path)
        logger.info("Downloading: {}".format(self.remote_path))
        if not dry_run:
            self.mirrorer.conn.get(
                self.remote_path, self.local_path, preserve_mtime=True
            )

    def run_rmkdir(self, dry_run):
        if self.remote_is_file:
            logger.info("Removing: {}".format(self.remote_path))
            if not dry_run:
                self.mirrorer.conn.remove(self.remote_path)
        logger.info("Making directory: {}".format(self.remote_path))
        if not dry_run:
            self.mirrorer.conn.makedirs(self.remote_path)

    def run_put(self, dry_run):
        if self.remote_is_file:
            logger.info("Removing: {}".format(self.remote_path))
            if not dry_run:
                self.mirrorer.conn.remove(self.remote_path)
        elif self.remote_is_dir:
            logger.info("Removing Directory: {}".format(self.remote_path))
            if not dry_run:
                self.mirrorer.rmtree(self.remote_path)
        logger.info("Downloading: {}".format(self.remote_path))
        if not dry_run:
            self.mirrorer.conn.put(
                self.local_path, self.remote_path, preserve_mtime=True
            )

    def to_json(self):
        return self.to_dict()

    def to_dict(self):
        result_dict = OrderedDict(
            [("action_code", self.action_code), ("path", self.remote_path)]
        )
        result_dict.update(self.kwargs)
        return result_dict

    def __repr__(self):
        args = ["{}={}".format(key, value) for key, value in self.to_dict().items()]
        args_string = ",".join(args)
        return "SFTPAction({})".format(args_string)
