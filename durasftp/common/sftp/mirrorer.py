#!/usr/bin/env python

"""
Mirrors an SFTP server
"""

import argparse
import stat
from argparse import ArgumentParser
from collections import OrderedDict
from os import scandir
from os.path import join, isdir, realpath

import arrow
import pysftp

from durasftp.common.log import add_logger_args, get_logger
from durasftp.common.sftp.action import SFTPAction
from durasftp.common.sftp.action_codes import SFTPActionCodes
from durasftp.common.sftp.action_list import SFTPActionList
from durasftp.common.sftp.connection import DurableSFTPConnection

EPILOG = __doc__

# Accepts any host key
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

# Leverage the logger module to avoid print statements
#
logger = get_logger(__name__)


def entry_is_dir(entry):
    return stat.S_ISDIR(entry.st_mode)


def entry_is_file(entry):
    return stat.S_ISREG(entry.st_mode)


class Mirrorer:
    WITH_TIMES = "WITH_TIMES"
    WITH_PERMS = "WITH_PERMS"

    def __init__(self, local_base, options=[], timeout=15, **kwargs):
        logger.info("Opening sftp://{}:{}".format(kwargs["host"], kwargs["port"]))
        self.conn = DurableSFTPConnection(cnopts=cnopts, timeout=timeout, **kwargs)
        # Realpath here ensures that trailing slashes will not cause issues
        self.local_base = realpath(local_base)
        self.action_list = SFTPActionList(self)
        self.remote_attr_tree = OrderedDict()
        self.local_attr_tree = OrderedDict()
        self.options = options
        self.conn.listdir("/")
        if self.conn and self.conn._transport:
            transport = self.conn._transport
            sock = transport.sock
            logger.info(
                "Opened sftp://{}:{} on socket: {}".format(
                    kwargs["host"], kwargs["port"], sock.fileno()
                )
            )

    def rmtree(self, remote_dir):
        """
        Deletes all files and directories on a remote server recursively
        :param remote_dir: The remote directory to delete
        """
        files_to_delete = []
        dirs_to_delete = []

        def mark_to_rmdir(remote_path):
            dirs_to_delete.append(remote_path)

        def mark_to_remove(remote_path):
            files_to_delete.append(remote_path)

        # First, write down every file and directory
        self.conn.walktree(remote_dir, mark_to_remove, mark_to_rmdir, None)
        mark_to_rmdir(remote_dir)

        # Files are always safe to delete
        for remote_file_path in files_to_delete:
            logger.info("Removing: {}".format(remote_file_path))
            self.conn.remove(remote_file_path)

        # Dirs need their children deleted first, since they must be empty
        # By sorting the paths by length, we ensure that child directories are deleted first
        sorted_dirs = sorted(
            dirs_to_delete, key=lambda sub_dir_path: len(sub_dir_path), reverse=True
        )
        for remote_dir_path in sorted_dirs:
            logger.info("Removing Dir: {}".format(remote_dir_path))
            self.conn.rmdir(remote_dir_path)

    def entries_match(self, local_entry, remote_entry):
        """
        Compares two dir/file entries to determine if a change is required.
        Compares file size and modification time
        :return: True if they are the same
        """
        if entry_is_dir(remote_entry):
            if local_entry.is_dir():
                return True
            elif local_entry.is_file():
                return False
        if entry_is_file(remote_entry):
            if local_entry.is_dir():
                return False
            elif local_entry.is_file():
                local_stat = local_entry.stat()
                local_modified_time = arrow.get(int(local_stat.st_mtime))
                local_size = local_stat.st_size
                remote_modified_time = arrow.get(int(remote_entry.st_mtime))
                remote_size = remote_entry.st_size
                if (
                    local_modified_time == remote_modified_time
                    and local_size == remote_size
                ):
                    return True
                else:
                    return False

    def remote_path_from_local(self, local_path):
        """
        Calculates the path on the remote, based on the local path
        """
        return local_path[len(self.local_base) :]

    def local_path_from_remote(self, remote_path):
        """
        Calculates the path on your local, based on the remote path
        """
        # TODO: Join these
        return self.local_base + remote_path

    def load_remote_dir_listing(self, remote_path):
        """
        Recursively loads the entire directory and subdirectory listing of a remote dir,
          and loads the results into the remote_attr_tree
        :param remote_path: A remote directory path
        """
        logger.info("Loading remote: {}".format(remote_path))
        remote_listing = self.conn.listdir_attr(remote_path)
        for remote_entry in remote_listing:
            remote_entry_path = join(remote_path, remote_entry.filename)
            self.remote_attr_tree[remote_entry_path] = remote_entry
            if entry_is_dir(remote_entry):
                self.load_remote_dir_listing(remote_entry_path)

    def load_local_dir_listing(self, remote_path):
        """
        Recursively loads the entire directory and subdirectory listing of a local dir,
          and loads the results into the local_attr_tree
        :param remote_path: A remote directory path
        """
        logger.info("Loading local: {}".format(remote_path))
        local_path = self.local_base + remote_path
        if isdir(local_path):
            local_listing = scandir(local_path)
            for local_entry in local_listing:
                child_remote_path = self.remote_path_from_local(local_entry.path)
                self.local_attr_tree[child_remote_path] = local_entry
                if local_entry.is_dir():
                    self.load_local_dir_listing(child_remote_path)

    def load_stat_trees(self):
        """
        Completely scans both local and remote directories
        :return:
        """
        # TODO: Add subdirectory loading, but default to "/"
        logger.info("Loading file listings")
        self.remote_attr_tree = OrderedDict()
        self.local_attr_tree = OrderedDict()
        self.load_remote_dir_listing("/")
        self.load_local_dir_listing("/")

    def action_from_remote_by_path(self, remote_path):
        """
        Calculates which SFTP action must be performed in order to mirror a remote
          dir/file onto the local system
        :param remote_path: A remote directory path
        :return: The SFTP action to be performed later
        :rtype: SFTPAction
        """
        remote_entry = self.remote_attr_tree[remote_path]
        if remote_path in self.local_attr_tree:
            # Entry exists locally
            local_entry = self.local_attr_tree[remote_path]
            if self.entries_match(local_entry, remote_entry):
                return SFTPAction(
                    self,
                    SFTPActionCodes.OK,
                    remote_path,
                    local_entry=local_entry,
                    remote_entry=remote_entry,
                )
            else:
                if entry_is_dir(remote_entry):
                    return SFTPAction(
                        self,
                        SFTPActionCodes.LMKDIR,
                        remote_path,
                        local_entry=local_entry,
                        remote_entry=remote_entry,
                    )
                elif entry_is_file(remote_entry):
                    return SFTPAction(
                        self,
                        SFTPActionCodes.GET,
                        remote_path,
                        local_entry=local_entry,
                        remote_entry=remote_entry,
                    )
        else:
            # Entry does not exist locally
            if entry_is_dir(remote_entry):
                return SFTPAction(
                    self, SFTPActionCodes.LMKDIR, remote_path, remote_entry=remote_entry
                )
            elif entry_is_file(remote_entry):
                return SFTPAction(
                    self, SFTPActionCodes.GET, remote_path, remote_entry=remote_entry
                )

    def action_to_remote_by_path(self, remote_path):
        """
        Calculates which SFTP action must be performed in order to mirror a local
          dir/file onto the remote system
        :param remote_path: A remote directory path
        :return: The SFTP action to be performed later
        :rtype: SFTPAction
        """
        local_entry = self.local_attr_tree[remote_path]
        if remote_path in self.remote_attr_tree:
            # Entry exists remotely
            remote_entry = self.remote_attr_tree[remote_path]
            if self.entries_match(local_entry, remote_entry):
                return SFTPAction(
                    self,
                    SFTPActionCodes.OK,
                    remote_path,
                    local_entry=local_entry,
                    remote_entry=remote_entry,
                )
            else:
                if local_entry.is_dir():
                    return SFTPAction(
                        self,
                        SFTPActionCodes.RMKDIR,
                        remote_path,
                        local_entry=local_entry,
                        remote_entry=remote_entry,
                    )
                elif local_entry.is_file():
                    return SFTPAction(
                        self,
                        SFTPActionCodes.PUT,
                        remote_path,
                        local_entry=local_entry,
                        remote_entry=remote_entry,
                    )
        else:
            # Entry does not exist remotely
            if local_entry.is_dir():
                return SFTPAction(
                    self, SFTPActionCodes.RMKDIR, remote_path, local_entry=local_entry
                )
            elif local_entry.is_file():
                return SFTPAction(
                    self, SFTPActionCodes.PUT, remote_path, local_entry=local_entry
                )

    def actions_to_mirror_from_remote(self):
        """
        Loads entire directory structure for both local and remote sources
          and determines what SFTP actions will need to be performed to mirror
          the content of the remote server to the local server
        :return: A list of SFTPActions
        :rtype: SFTPActionList
        """
        # TODO: Allow subdirectory mirror
        self.load_stat_trees()
        self.action_list = SFTPActionList(self)
        for remote_path in self.remote_attr_tree.keys():
            action = self.action_from_remote_by_path(remote_path)
            self.action_list.add(action)
        return self.action_list

    def actions_to_mirror_to_remote(self):
        """
        Loads entire directory structure for both local and remote sources
          and determines what SFTP actions will need to be performed to mirror
          the content of the local server to the remote server
        :return: A list of SFTPActions
        :rtype: SFTPActionList
        """
        # TODO: Allow subdirectory mirror
        self.load_stat_trees()
        self.action_list = SFTPActionList(self)
        for remote_path in self.local_attr_tree.keys():
            action = self.action_to_remote_by_path(remote_path)
            self.action_list.add(action)
        return self.action_list

    def mirror_from_remote(self, callback=None, dry_run=False):
        """
        Mirrors from the remote server to the local server
        :param callback:
        :param dry_run:
        :return:
        """
        # TODO: Document params
        # TODO: Add filter param fn
        # TODO: Allow sync of subdirectories
        self.actions_to_mirror_from_remote()
        self.action_list.do_actions(callback=callback, dry_run=dry_run)

    def mirror_to_remote(self, callback=None, dry_run=False):
        """
        Mirrors from the local server to the remote server
        :param callback:
        :param dry_run:
        :return:
        """
        # TODO: Document params
        # TODO: Add filter param fn
        # TODO: Allow sync of subdirectories
        self.actions_to_mirror_to_remote()
        self.action_list.do_actions(callback=callback, dry_run=dry_run)

    def close(self):
        """
        Close the SFTP connection socket
        """
        if self.conn._transport:
            transport = self.conn._transport
            sock = transport.sock
            logger.info("Closing socket: {}".format(sock.fileno()))
        self.conn.close()


def parse_arguments():
    parser = ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=EPILOG
    )
    parser.add_argument(
        "--local-base", help="Local directory to mirror with", required=True
    )
    parser.add_argument("--host", help="SFTP server IP/FQDN", required=True)
    parser.add_argument("--username", help="SFTP username", required=True)
    parser.add_argument("--password", help="SFTP password")
    parser.add_argument("--private-key", help="Path to a private key file")
    parser.add_argument(
        "--private-key-pass", help="Password to an encrypted private key file"
    )
    parser.add_argument("--port", default=22, help="SFTP port", type=int)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Don't actually do anything, just print what would be done",
    )
    add_logger_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    # TODO: Add subdirectory mirror
    # TODO: Add regex filter option
    args = parse_arguments()
    mirrorer = Mirrorer(
        local_base=args.local_base,
        host=args.host,
        username=args.username,
        port=args.port,
        password=args.password,
        private_key=args.private_key,
        private_key_pass=args.private_key_pass,
    )
    mirrorer.mirror_from_remote(dry_run=False)
    filtered_stuff = mirrorer.action_list
    for remote_path, action in filtered_stuff:
        # TODO: Improve UX
        print(action)
    mirrorer.close()
