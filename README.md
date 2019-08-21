# DuraSFTP

A durable extension the pysftp SFTP client: https://pysftp.readthedocs.io/

## Installation

```bash
pip install durasftp
```

## Command Line Usage

Show the help:

```bash
python -m durasftp --help
```

Mirror an SFTP endpoint to your local with private keys:

```bash
python -m durasftp --host some.sftp.server.com --port 22 --username your_username \
  --private-key ~/.ssh/id_rsa --private-key-pass 'ULTRASECUREPASSWORD' \
  --local-base /tmp/local_copy_of_server
```

Mirror an SFTP endpoint to your local with a password:

```bash

python -m durasftp --host some.sftp.server.com --port 22 --username your_username \
  --password 'ULTRASECUREPASSWORD' \
  --local-base /tmp/local_copy_of_server
```

## Package Usage

This package very closely mirrors the functionality of pysftp, except it automatically 
recovers a connection in the event that network connectivity is intermittent.

It also introduces a mirroring functionality, where you can copy a local directory to
a remote server, or copy a remote directory to the local. It will ignore files that
already exist on the destination, if the file size and modification time are identical.

### Basic Usage

The DurableSFTPConnection class is intended to be a drop-in replacement for the
pysftp.Connection class. With a stable network connection, it should be identical in
every way.

```python
from durasftp import DurableSFTPConnection

conn = DurableSFTPConnection(host="some.sftp.server.com", port=22, username="your_username", password="ULTRASECUREPASSWORD")
conn.listdir('/')
```

### Mirror from remote server to local

```python
from durasftp import Mirrorer

mirrorer = Mirrorer(
    local_base="/tmp/local_copy_of_server",
    host="some.sftp.server.com",
    port=22,
    username="your_username",
    password="ULTRASECUREPASSWORD",
    timeout=3,
)
mirrorer.mirror_from_remote(dry_run=True)
```
