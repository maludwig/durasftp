#!/usr/bin/env python
from os import getcwd, remove, rmdir
from shutil import rmtree

import pysftp

from common.sftp.action_codes import SFTPActionCodes
from common.sftp.mirrorer import Mirrorer
from argparse import ArgumentParser
from common.log import add_logger_args

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

LOCAL_BASE = "/Users/mitchell.ludwig/dev/sftping/docker/_mirror/foo"

if __name__ == "__main__":
    parser = ArgumentParser()
    add_logger_args(parser)
    parser.parse_args()

    # srv = pysftp.Connection(host="qa-sftp-mft.solium.com", username="qa_ubs_source", password="q1w2e3r4")
    # srv = pysftp.Connection(host="qa-sftp-mft.solium.com", username="dev_ms_source", private_key="~/.ssh/yyc-stg-pentaho01-2017-11-24.pem")
    # srv = pysftp.Connection(host="qa-sftp-mft.solium.com", username="dev_ms_source", private_key="~/.ssh/mitchell.ludwig-2018-01-08.pem", private_key_pass="@WSXooRed#f00")
    # srv = pysftp.Connection(host="localhost", username="foo", password="pass", port=2022, cnopts=cnopts)
    # print("---")
    # print(getcwd())
    # with pysftp.cd('/Users/mitchell.ludwig/dev/sftping/docker/_mirror/foo/pap'):
    #     print("---")
    #     print("Srv: {}".format(srv.getcwd()))
    #     print("OS: {}".format(getcwd()))
    # print("---")
    # print(getcwd())
    # with pysftp.cd('/Users/mitchell.ludwig/dev/sftping/docker/_mirror/foo/'):
    #     with srv.cd('/'):
    #         print("---")
    #         print("Srv: {}".format(srv.getcwd()))
    #         print("OS: {}".format(getcwd()))
    #         srv.get('09-last-week-tonight-w1200-h630.jpg', preserve_mtime=True)
    #
    # exit()
    # data = srv
    # print("Data: ")
    # print(data)
    # srv.close()

    # mirrorer = Mirrorer(local_base=LOCAL_BASE, host="secure-xfer.ubs.com", username="papsw", password="Welcome@123")
    # mirrorer = Mirrorer(local_base=LOCAL_BASE, host="qa-sftp-mft.solium.com", username="qa_ubs_source", password="q1w2e3r4")
    mirrorer = Mirrorer(local_base=LOCAL_BASE, host="localhost", username="foo", password="pass", port=2022)
    # mirrorer.load_stat_trees()
    # mirrorer.actions_to_mirror_from_remote()
    # mirrorer.mirror_from_remote(dry_run=True)
    # remove('/Users/mitchell.ludwig/dev/sftping/docker/_mirror/foo/pap/PRD/lyv/imports/jennifer-lawrence.jpg')
    rmtree('/Users/mitchell.ludwig/dev/sftping/docker/_mirror/foo/pap/PRD/lyv')
    mirrorer.mirror_from_remote(dry_run=False)
    filtered_stuff = mirrorer.action_list.filtered_items()
    for remote_path, action in filtered_stuff:
        print(action)
    filtered_stuff = mirrorer.action_list.filtered_items(codes=[SFTPActionCodes.LMKDIR])
    for remote_path, action in filtered_stuff:
        print(action)
    # action_list = mirrorer.walk()
    # for path, action in action_list.items():
    #     print(path, action)

    # action_list = SFTPActionList(mirrorer)
    # action_list.add(SFTPActionCodes.LMKDIR, "/tmp/hi")
    # action_list.do_actions(dry_run=True)
    mirrorer.close()
    print("CLOSED")

    # # Prints out the directories and files, line by line
    # for i in data:
    #     print(i)
    #
    # # for x in sorted(scandir("/Users/mitchell.ludwig/sync/_mirror/qa-sftp-mft.solium.com/dev_ms_source/")):
    # for x in sorted(scandir(LOCAL_BASE), key=attrgetter("name")):
    #     print(x)

    print("Hi")
