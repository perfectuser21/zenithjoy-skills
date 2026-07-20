#!/usr/bin/env bash
# 回归测试：2026-07-19/20 磁盘反复告急事故
# ①cron 默认 PATH 找不到 /opt/homebrew/bin 下的 npm/brew/docker，daily 清理长期跳过这三步
# ②磁盘检测查的是 / （APFS 只读系统卷，长期~30%），不是真实数据卷 /System/Volumes/Data（曾到95%），
#   导致 70% 告警从未触发
# 用法：bash janitor/tests/test-cron-path-and-diskvol.sh
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JANITOR="$SCRIPT_DIR/janitor.sh"
FAIL=0

echo "=== 测试1：脚本必须在顶部显式导出 PATH，覆盖 /opt/homebrew/bin ==="
if grep -q 'export PATH=.*opt/homebrew/bin' "$JANITOR"; then
  echo "  ✓ 找到显式 PATH 导出"
else
  echo "  ✗ 未找到显式 PATH 导出——cron 默认 PATH（/usr/bin:/bin）下 npm/brew/docker 检测必然失败"
  FAIL=1
fi

echo ""
echo "=== 测试2：模拟 cron 环境（裸 PATH）跑 daily，npm/brew/docker 检测不能因 PATH 失败 ==="
# 只要三个二进制在本机 /opt/homebrew/bin 真实存在，模拟 cron 裸 PATH 后仍应通过 command -v 检测到
for bin in npm brew docker; do
  real_path=$(env -i HOME="$HOME" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" bash -c "command -v ${bin}" 2>/dev/null)
  bare_cron_path=$(env -i HOME="$HOME" PATH="/usr/bin:/bin" bash -c "command -v ${bin}" 2>/dev/null)
  if [ -z "$real_path" ]; then
    echo "  ⚠ 本机没装 ${bin}，跳过该项校验"
    continue
  fi
  if [ -n "$bare_cron_path" ]; then
    echo "  ⚠ ${bin} 意外地在裸 PATH 下也能找到，本测试对该二进制无意义（跳过）"
    continue
  fi
  # 裸 cron PATH 下找不到，但脚本自己 export 过 PATH 之后应该能找到。
  # 只提取脚本里 PATH 导出那一行单独 source，不跑全脚本（避免触发真实清理副作用）。
  path_line=$(grep -m1 '^export PATH=' "$JANITOR")
  if [ -z "$path_line" ]; then
    echo "  ✗ ${bin}：脚本没有 PATH 导出行，裸 cron PATH 下必然找不到 ${bin}"
    FAIL=1
    continue
  fi
  found=$(env -i HOME="$HOME" PATH="/usr/bin:/bin" bash -c "$path_line; command -v ${bin}" 2>/dev/null)
  if [ -n "$found" ]; then
    echo "  ✓ ${bin}：脚本的 PATH 导出行能让裸 cron 环境找到它（$found）"
  else
    echo "  ✗ ${bin}：即使套用脚本的 PATH 导出行，裸 cron 环境仍找不到"
    FAIL=1
  fi
done

echo ""
echo "=== 测试3：磁盘检测必须查 /System/Volumes/Data，不能只查 / ==="
df_root_pct=$(df / 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
df_data_pct=$(df /System/Volumes/Data 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
echo "  当前本机：df / = ${df_root_pct}%，df /System/Volumes/Data = ${df_data_pct}%"

if grep -qE 'df[[:space:]]+/[[:space:]]|df[[:space:]]+-h[[:space:]]+/[[:space:]]|df[[:space:]]+/["'"'"']?$' "$JANITOR"; then
  echo "  ✗ 脚本里仍有直接查 / 的 df 调用（未查数据卷）"
  FAIL=1
else
  echo "  ✓ 脚本没有裸查 / 的 df 调用"
fi

if grep -q 'DISK_VOL=.*System/Volumes/Data' "$JANITOR"; then
  echo "  ✓ 脚本定义了 DISK_VOL=/System/Volumes/Data"
else
  echo "  ✗ 脚本没有定义 DISK_VOL 指向真实数据卷"
  FAIL=1
fi

disk_vol_usages=$(grep -c 'df.*"\$DISK_VOL"' "$JANITOR" 2>/dev/null)
[ -z "$disk_vol_usages" ] && disk_vol_usages=0
if [ "$disk_vol_usages" -ge 4 ]; then
  echo "  ✓ 脚本里 df \"\$DISK_VOL\" 用了 $disk_vol_usages 次（BEFORE/AFTER/CURRENT/USAGE_PCT 四处都应覆盖）"
else
  echo "  ✗ 脚本里 df \"\$DISK_VOL\" 只用了 $disk_vol_usages 次，应至少 4 处（BEFORE/AFTER/CURRENT/USAGE_PCT）"
  FAIL=1
fi

echo ""
echo "=== 测试4：frequent 模式必须包含已退出容器清理（daily 单次频率追不上堆积速度）==="
if awk '/MODE" = "frequent"/,/^fi$/' "$JANITOR" | grep -q "docker container prune"; then
  echo "  ✓ frequent 模式里找到 docker container prune"
else
  echo "  ✗ frequent 模式里没有 docker container prune —— daily 单次清理追不上 harness relay 容器堆积速度"
  FAIL=1
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "=== 全部通过 ==="
  exit 0
else
  echo "=== 有失败项 ==="
  exit 1
fi
