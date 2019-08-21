#!/usr/bin/env python
"""
CLI for durable SFTP communications
"""

import os
from argparse import RawDescriptionHelpFormatter, ArgumentParser

from durasftp import Mirrorer

EPILOG = __doc__


def main(args):
    print(args)
    auth_args = {}
    if args.private_key is not None:
        auth_args["private_key"] = args.private_key
    if args.private_key is not None:
        auth_args["private_key_pass"] = args.private_key_pass
    if args.password is not None:
        auth_args["password"] = args.password

    mirrorer = Mirrorer(
        local_base=args.local_base,
        host=args.host,
        username=args.username,
        port=args.port,
        timeout=args.timeout,
        **auth_args
    )
    mirrorer.mirror_from_remote(lambda action: print(action), dry_run=args.dry_run)


if __name__ == "__main__":
    cwd = os.getcwd()
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        epilog=EPILOG,
        description="Durable SFTP Client",
    )
    parser.add_argument(
        "--local-base", help="The local directory to mirror", type=str, default=cwd
    )
    parser.add_argument(
        "--host", help="The remote SFTP server hostname or IP", type=str, required=True
    )
    parser.add_argument("--port", help="The remote SFTP port", type=int, default=22)
    parser.add_argument("--timeout", help="The connection timeout", type=int, default=5)
    parser.add_argument(
        "--dry-run",
        help="Do not actually do anything, only print the things that would have been done",
        action="store_true",
    )
    parser.add_argument(
        "--username", help="The remote SFTP username", type=str, required=True
    )
    parser.add_argument("--password", help="The remote SFTP password", type=str)
    parser.add_argument(
        "--private-key", help="The path to a private key file", type=str
    )
    parser.add_argument(
        "--private-key-pass", help="The password to the private key file", type=str
    )

    parsed_arguments = parser.parse_args()
    main(parsed_arguments)
