#!/bin/bash
# Starts the local MySQL server without needing root or sudo permissions
SOCKET="/tmp/mysql.sock"
DATADIR="/tmp/mysql_data"

if [ -S "$SOCKET" ] && mysqladmin --socket="$SOCKET" -u root ping >/dev/null 2>&1; then
    echo "MySQL is already running on $SOCKET."
    exit 0
fi

if [ ! -d "$DATADIR" ]; then
    echo "Initializing MySQL data directory in $DATADIR..."
    mkdir -p "$DATADIR"
    mysqld --no-defaults --initialize-insecure --datadir="$DATADIR"
fi

echo "Starting MySQL server without root/sudo..."
mysqld --no-defaults --datadir="$DATADIR" --socket="$SOCKET" --port=3307 --bind-address=127.0.0.1 --mysqlx=OFF >/dev/null 2>&1 &

for i in $(seq 1 10); do
    sleep 1
    if [ -S "$SOCKET" ] && mysqladmin --socket="$SOCKET" -u root ping >/dev/null 2>&1; then
        echo "MySQL server successfully started on $SOCKET!"
        exit 0
    fi
done

echo "Error: MySQL failed to start within 10 seconds."
exit 1
