#!/usr/bin/env python
from common.sftp.mirrorer import Mirrorer

LOCAL_BASE = "/Users/mitchell.ludwig/dev/sftping/docker/mirror/foo"



# srv = pysftp.Connection(host="qa-sftp-mft.solium.com", username="qa_ubs_source", password="q1w2e3r4")
# srv = pysftp.Connection(host="qa-sftp-mft.solium.com", username="dev_ms_source", private_key="~/.ssh/yyc-stg-pentaho01-2017-11-24.pem")
# srv = pysftp.Connection(host="qa-sftp-mft.solium.com", username="dev_ms_source", private_key="~/.ssh/mitchell.ludwig-2018-01-08.pem", private_key_pass="@WSXooRed#f00")

# data = srv
# print("Data: ")
# print(data)
# srv.close()

mirrorer = Mirrorer(local_base=LOCAL_BASE, host="secure-xfer.ubs.com", username="papsw", password="Welcome@123")
# mirrorer = Mirrorer(local_base=LOCAL_BASE, host="qa-sftp-mft.solium.com", username="qa_ubs_source", password="q1w2e3r4")
# mirrorer = Mirrorer(local_base=LOCAL_BASE, host="localhost", username="foo", password="pass", port=2022)
# mirrorer.load_stat_trees()
mirrorer.actions_to_mirror_from_remote()
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
# # for x in sorted(scandir("/Users/mitchell.ludwig/sync/mirror/qa-sftp-mft.solium.com/dev_ms_source/")):
# for x in sorted(scandir(LOCAL_BASE), key=attrgetter("name")):
#     print(x)

print("Hi")
