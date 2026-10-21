#!/bin/bash
# mcp 嵌入式引擎同步+一致性门禁(F10 类防错配:两副本 sha 必须一致)
# 用法: bash mcp/sync_engine.sh   (在 skill 根目录执行)
# 发布链必跑:pkg/pyproject 分发只含 mcp/,引擎以副本形态进包——
# trunk scripts/verify_refs.py 与 mcp/verify_refs.py 逐字节一致才许发。
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/scripts/verify_refs.py"
DST="$ROOT/mcp/verify_refs.py"
cp "$SRC" "$DST"
A=$(sha256sum "$SRC" | cut -d' ' -f1)
B=$(sha256sum "$DST" | cut -d' ' -f1)
if [ "$A" != "$B" ]; then
  echo "[sync_engine] FAIL: sha 不一致($A vs $B)"; exit 1
fi
V1=$(grep -m1 '^VERSION' "$SRC" | sed 's/.*"\(.*\)".*/\1/')
V2=$(grep -m1 '^VERSION' "$DST" | sed 's/.*"\(.*\)".*/\1/')
[ "$V1" = "$V2" ] || { echo "[sync_engine] FAIL: VERSION 不一致($V1 vs $V2)"; exit 1; }
echo "[sync_engine] PASS: verify_refs.py 已同步(sha ${A:0:16}, VERSION $V1)"
