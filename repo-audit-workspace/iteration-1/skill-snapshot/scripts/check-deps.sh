#!/bin/bash
# check-deps.sh — 根目录依赖安全扫描
REPO=${1:-.}; cd $REPO
echo "=== 依赖安全扫描（根目录，含 dev deps）==="
[ -f "package.json" ] && npm audit --audit-level=high 2>/dev/null | grep -E "critical|high|vulnerabilities" | tail -3
[ -f "requirements.txt" ] || [ -f "pyproject.toml" ] && (pip audit 2>/dev/null | tail -3 || echo "pip audit 未安装")
echo "⚠️ 提醒：CI 中 --omit=dev 或只扫子目录会导致虚假 0 漏洞"
