#!/bin/bash
# Stops the user-level MySQL server started by start_mysql.sh
SOCKET="/tmp/mysql.sock"

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop mysql-local 2>/dev/null
fi

if [ -S "$SOCKET" ]; then
    mysqladmin --socket="$SOCKET" -u root shutdown 2>/dev/null
fi

pkill -f "mysqld.*socket=/tmp/mysql.sock" 2>/dev/null
echo "Local MySQL server stopped."
