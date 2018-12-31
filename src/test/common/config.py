from collections import OrderedDict
from os.path import dirname, isdir, join
import json

REPO_ROOT = dirname(dirname(dirname(dirname(__file__))))
if not isdir(join(REPO_ROOT, '.git')):
    raise Exception("Bad repo root mapping, could not find .git under: {}".format(REPO_ROOT))


## NOTE: The hostname resolves to both IPv6 and IPv4 addresses, causing a warning in paramiko
# SFTP_HOST = "localhost"
SFTP_HOST = "127.0.0.1"

SFTP_USER = 'dev_ms_source'
SFTP_PASS = 'ULTRASECUREPASSWORD'
SFTP_PORT = 2022
SFTP_MOUNT = join(REPO_ROOT, "tmp/_sftp")
SFTP_BASE = join(SFTP_MOUNT, SFTP_USER)

LOCAL_BASE = join('/tmp/zug', REPO_ROOT, "tmp/_local", SFTP_USER)

FULL_CONFIG = OrderedDict([
    ("REPO_ROOT", REPO_ROOT),
    ("LOCAL_BASE", LOCAL_BASE),
    ("SFTP_HOST", SFTP_HOST),
    ("SFTP_BASE", SFTP_BASE),
    ("SFTP_USER", SFTP_USER),
    ("SFTP_PASS", SFTP_PASS),
    ("SFTP_PORT", SFTP_PORT),
])

if __name__ == "__main__":
    print(json.dumps(FULL_CONFIG, indent=2))