#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

if [ -f .pid ]; then
    PID=$(cat .pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm .pid
        echo "Stopped process $PID"
    else
        rm .pid
        echo "Process $PID not running"
    fi
else
    echo "No .pid file found"
fi
