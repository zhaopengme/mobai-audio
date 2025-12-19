#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境
source .venv/bin/activate

# 创建日志目录
mkdir -p logs

# 日志文件（按日期）
LOG_FILE="logs/tts-$(date +%Y%m%d).log"

# 后台启动，输出到日志
nohup python main.py >> "$LOG_FILE" 2>&1 &

# 保存 PID
echo $! > .pid
echo "Started with PID: $!"
echo "Log file: $LOG_FILE"
