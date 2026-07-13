#!/usr/bin/env bash
# Integrity self-check + auto-materialize for the meta-analysis skill.
# 技能完整性自检：确认 scripts/ 含必要的 R 代码文件；
# 若缺失，从内嵌的 Python 模板 (r_templates.py) 自动生成，无需用户手动下载。
#
# Usage / 用法:  bash scripts/check_integrity.sh
# 退出码 0 = 完整(或已自动生成); 非 0 = 生成失败。

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPTS="$SKILL_ROOT/scripts"
TEMPLATE="$SCRIPTS/r_templates.py"

R_FILES=(meta_analysis_core.R effect_size_conversions.R network_meta_analysis.R setup_packages.R stata_equivalents.R)

# 1) 若 .R 齐全，直接通过
missing=0
for f in "${R_FILES[@]}"; do
  [ -f "$SCRIPTS/$f" ] || missing=1
done
if [ "$missing" -eq 0 ]; then
  echo "OK: scripts/ 完整，检测到 ${#R_FILES[@]} 个 .R 文件。"
  exit 0
fi

# 2) 缺失 -> 尝试从内嵌 Python 模板自动生成
if [ -f "$TEMPLATE" ]; then
  echo "检测到部分 R 代码缺失，正在从内嵌模板自动生成..."
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python  >/dev/null 2>&1; then PY=python
  else PY=""
  fi
  if [ -n "$PY" ]; then
    (cd "$SCRIPTS" && "$PY" r_templates.py) && echo "R 代码已从模板生成。" || echo "⚠️ 模板生成失败。"
  else
    echo "⚠️ 未找到 python，无法自动生成 R 代码。"
  fi
  # 重新检查
  missing=0
  for f in "${R_FILES[@]}"; do
    [ -f "$SCRIPTS/$f" ] || missing=1
  done
  if [ "$missing" -eq 0 ]; then
    echo "OK: R 代码已自动生成，共 ${#R_FILES[@]} 个 .R 文件。"
    exit 0
  fi
fi

# 3) 生成失败（罕见：如 python 缺失或模板文件损坏）
echo "⚠️  R 代码生成失败：请确认已安装 Python，并重试 bash scripts/check_integrity.sh"
exit 1
