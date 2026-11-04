#!/usr/bin/env bash
# 旧engine-ship无PR验真就completed的入口已退休；禁止兼容调用伪报合并。
set -euo pipefail
printf '%s\n' 'SHIP_RETIRED: 此入口不再写Task终态；候选交付使用实际加载engine-ship的同release helper，终态交engine-pr-watchdog验真。' >&2
exit 12
