#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

find "$SCRIPT_DIR" -name '__pycache__' -exec rm -rf {} \; > /dev/null
find "$SCRIPT_DIR" -name '.DS_Store' -exec rm {} \;
