#!/bin/bash
# Starts the local MySQL server without needing root or sudo permissions
SOCKET="/tmp/mysql.sock"
DATADIR="/tmp/mysql_data"

if [ -S "$SOCKET" ] && mysqladmin --socket="$SOCKET" -u root ping >/dev/null 2>&1; then
    echo "MySQL is already running on $SOCKET."
    exit 0
fi

if [ ! -d "$DATADIR/mysql" ]; then
    echo "Initializing MySQL data directory in $DATADIR..."
    rm -rf "$DATADIR"
    mkdir -p "$DATADIR"
    mysqld --no-defaults --initialize-insecure --datadir="$DATADIR"
fi

echo "Starting MySQL server without root/sudo..."
if command -v systemd-run >/dev/null 2>&1 && systemctl --user status >/dev/null 2>&1; then
    systemctl --user stop mysql-local 2>/dev/null
    systemd-run --user --unit=mysql-local /usr/sbin/mysqld --no-defaults --datadir="$DATADIR" --socket="$SOCKET" --port=3307 --bind-address=127.0.0.1 --mysqlx=OFF >/dev/null 2>&1
else
    nohup mysqld --no-defaults --datadir="$DATADIR" --socket="$SOCKET" --port=3307 --bind-address=127.0.0.1 --mysqlx=OFF >/tmp/mysqld_userspace.log 2>&1 &
fi

CURRENT_USER="${USER:-mint}"

for i in $(seq 1 10); do
    sleep 1
    if [ -S "$SOCKET" ] && mysqladmin --socket="$SOCKET" -u root ping >/dev/null 2>&1; then
        echo "MySQL server successfully started on $SOCKET!"
        mysql --socket="$SOCKET" -u root -e "
            CREATE DATABASE IF NOT EXISTS hospital;
            CREATE USER IF NOT EXISTS '${CURRENT_USER}'@'localhost' IDENTIFIED BY '';
            GRANT ALL PRIVILEGES ON *.* TO '${CURRENT_USER}'@'localhost' WITH GRANT OPTION;
            FLUSH PRIVILEGES;
        " >/dev/null 2>&1
        exit 0
    fi
done

echo "Error: MySQL failed to start within 10 seconds."
exit 1
