#!/usr/bin/env bash
# 境外搜索量报告 — 每日自动部署脚本
# 功能：更新数据 → 推送到 GitHub → 触发 Pages 更新

set -e

REPORT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$REPORT_DIR/deploy.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始部署..." >> "$LOG"

cd "$REPORT_DIR"

# 检查是否有变更
git add external.html internal.html index.html
if git diff --cached --quiet; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 数据无变化，跳过推送" >> "$LOG"
    exit 0
fi

git commit -m "📊 每日自动更新 $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
git push origin main >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 推送成功" >> "$LOG"
