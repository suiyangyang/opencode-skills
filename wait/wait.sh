#!/bin/bash
# 等待指定时间
# 用法: ./wait.sh [秒数]
# 默认等待 300 秒 (5分钟)

SECONDS="${1:-300}"

echo "等待 ${SECONDS} 秒..."
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"

sleep "$SECONDS"

echo "结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "等待完成"