#!/usr/bin/env bash
# 境外搜索量趋势报告 — 每日10:30更新脚本
# 功能：从RedBI取最新近14天数据，写入index.html的RAW_DATA变量

set -e

SKILL_DIR=~/.openclaw/workspace/skills/bi-data-fetch
REPORT_DIR=~/.openclaw/workspace/outbound-search-report
LOG="$REPORT_DIR/update.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始更新境外搜索量报告..." >> "$LOG"

# 取数
RESULT=$(python3 "$SKILL_DIR/scripts/fetch_chart_data.py" \
  --chart-url "https://insight.devops.xiaohongshu.com/self-service?resourceId=40729&shortcutId=15258238" \
  --query "提取全部数据，包含境外城市、脱敏社区搜索量、周环比变化率、年同比变化率" 2>&1)

if [ $? -ne 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 取数失败: $RESULT" >> "$LOG"
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 取数成功，开始生成报告..." >> "$LOG"

# 用Python解析并重新生成HTML
python3 "$REPORT_DIR/gen_html.py" "$RESULT" && \
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 报告生成完成" >> "$LOG" || \
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 报告生成失败" >> "$LOG"
