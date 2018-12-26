import stat
import sys
from collections import OrderedDict
from os import scandir
from os.path import join, isdir, basename

import pysftp
import arrow

from common.sftp.action import SFTPAction
from common.sftp.action_codes import SFTPActionCodes
from common.sftp.action_list import SFTPActionList

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None


def entry_is_dir(entry):
    return stat.S_ISDIR(entry.st_mode)


def entry_is_file(entry):
    return stat.S_ISREG(entry.st_mode)


class Mirrorer:
    WITH_TIMES = "WITH_TIMES"
    WITH_PERMS = "WITH_PERMS"

    def __init__(self, local_base, options=[], **kwargs):
        self.conn = pysftp.Connection(cnopts=cnopts, **kwargs)
        self.local_base = local_base
        self.action_list = SFTPActionList(self)
        self.remote_attr_tree = OrderedDict()
        self.local_attr_tree = OrderedDict()
        self.options = options

    def remote_path_from_local(self, local_path):
        return local_path[len(self.local_base):]

    def load_remote_dir_listing(self, remote_path):
        print("Loading remote: {}".format(remote_path), flush=True)
        remote_listing = self.conn.listdir_attr(remote_path)
        for remote_entry in remote_listing:
            remote_entry_path = join(remote_path, remote_entry.filename)
            self.remote_attr_tree[remote_entry_path] = remote_entry
            if entry_is_dir(remote_entry):
                self.load_remote_dir_listing(remote_entry_path)

    def load_local_dir_listing(self, remote_path):
        local_path = self.local_base + remote_path
        if isdir(local_path):
            local_listing = scandir(local_path)
            for local_entry in local_listing:
                remote_path = self.remote_path_from_local(local_entry.path)
                self.local_attr_tree[remote_path] = local_entry
                if local_entry.is_dir():
                    self.load_local_dir_listing(remote_path)

    def load_stat_trees(self):
        print("Listing remote:")
        self.remote_attr_tree = OrderedDict()
        self.local_attr_tree = OrderedDict()
        self.load_remote_dir_listing("/")
        # self.load_local_dir_listing("/")
        # print(self.remote_attr_tree)
        listing_path = "/tmp/ubs" + arrow.get().format("YYYY-MM-DDTHH-mm-ss") + "Z.csv"
        with open(listing_path, "w") as listing_file:
            for remote_path, remote_entry in self.remote_attr_tree.items():
                if entry_is_file(remote_entry):
                    remote_mtime = arrow.get(remote_entry.st_mtime).to('America/Edmonton')
                    listing_file.write("{}|{}|{}\n".format(remote_mtime, remote_path, remote_entry.st_size))
                    if "exports" in remote_path:
                        if basename(remote_path) in (
                                'assignment.txt',
                                'empl.txt',
                                'empltax.txt',
                                'exer.txt',
                                'exertax.txt',
                                'general.txt',
                                'grant.txt',
                                'granttax.txt',
                                'perfvest.txt',
                                'taxrate.txt',
                        ):
                            print("Deleting: " + remote_path, flush=True)
                            self.conn.remove(remote_path)

    def action_from_remote_by_path(self, remote_path):
        remote_entry = self.remote_attr_tree[remote_path]
        if remote_path in self.local_attr_tree:
            local_entry = self.local_attr_tree[remote_path]
            local_stat = local_entry.stat()
            print(local_entry)
            print(local_stat)
        else:
            if entry_is_dir(remote_entry):
                return SFTPAction(self, SFTPActionCodes.LMKDIR, remote_path, mode=remote_entry.st_mode)
            elif entry_is_file(remote_entry):
                return SFTPAction(self, SFTPActionCodes.GET, remote_path, mode=remote_entry.st_mode)

    def actions_to_mirror_from_remote(self):
        self.load_stat_trees()
        self.action_list = SFTPActionList(self)
        for remote_path in self.remote_attr_tree.keys():
            action = self.action_from_remote_by_path(remote_path)
            self.action_list.add(action)

        # for remote_entry_path, remote_entry in self.remote_attr_tree:
        #     if entry_is_dir(remote_entry):
        #         if
        #
        # remote_listing = self.conn.listdir_attr(remote_path)
        # local_path = self.local_base + remote_path
        # if isdir(local_path):
        #     local_listing = scandir(local_path)
        #     for remote_entry in remote_listing:
        #         print(remote_entry)
        #     for local_entry in local_listing:
        #         print(local_entry)
        # else:
        #     for remote_entry in remote_listing:
        #         remote_entry_path = join(remote_path, remote_entry.filename)
        #         if entry_is_dir(remote_entry):
        #             self.action_list.add(SFTPActionCodes.LMKDIR, remote_entry_path, mode=remote_entry.st_mode)
        #         elif entry_is_file(remote_entry):
        #             self.action_list.add(SFTPActionCodes.GET, remote_entry_path, mode=remote_entry.st_mode)

    def compare_attrs(self, remote_entry, local_entry):
        print(remote_entry)
        print(local_entry)

    def file_cb(self, remote_path):
        print("File Path: %s" % remote_path)

    def dir_cb(self, remote_path):
        print("Directory Path: %s" % remote_path)
        self.compare_remote_dir_to_local(remote_path)
        # data = self.conn.listdir_attr(path)
        # for entry in data:
        #     print(entry)
        #     print("Is dir: %s" % entry_is_dir(entry))

    def unknown_cb(self, remote_path):
        print("Unknown Path: %s" % remote_path)

    def walk(self):
        self.conn.walktree("/", self.file_cb, self.dir_cb, self.unknown_cb)
        return self.action_list

    def close(self):
        self.conn.close()
