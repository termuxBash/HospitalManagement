#!/bin/bash
# Convenient wrapper for MySQL client connecting to the active socket
exec mysql --socket=/tmp/mysql.sock "$@"
