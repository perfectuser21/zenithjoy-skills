---
name: nas
description: |
  NAS 内容管理工具。封装 nas-content-manager.sh，支持列出、查看、读取、更新、搜索、统计 NAS 上的内容。
  当用户问 NAS 上有什么内容、查看某个内容详情、更新内容状态、搜索内容、或查看 NAS 统计数据时触发。
  触发词：/nas、NAS 内容、查一下 NAS、NAS 上有什么、NAS 容量、NAS 统计、内容状态更新。
---

# NAS 内容管理 Skill

## 触发方式

- `/nas <command> [args]`
- 用户提到"NAS 内容"、"管理内容"、"查看内容"

## 功能

封装 `infrastructure/scripts/nas-content-manager.sh`，提供友好的内容管理接口。

## 工具路径

`/home/xx/perfect21/infrastructure/scripts/nas-content-manager.sh`

## 使用示例

```bash
/nas list                              # 列出所有内容
/nas show 2025-11-03-009a0b            # 查看详情
/nas read 2025-11-03-009a0b            # 读取文本
/nas update-status <id> ready          # 更新状态
/nas stats                             # 统计信息
```

## 命令说明

调用时执行：`bash /home/xx/perfect21/infrastructure/scripts/nas-content-manager.sh <command> [args]`
