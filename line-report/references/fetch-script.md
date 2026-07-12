# fetch_line_data — 取数脚本（唯一代码块，原样落盘执行）

用法见 SKILL.md Step 1。把下面代码块写到 scratchpad 后 `python3` 执行，仅依赖标准库。

```python
#!/usr/bin/env python3
"""line-report 数据抓取：按 Line(journey) 聚合任务完成/决策/PR 合并，含上一周期环比。

只做硬字段归属（payload.journey_id / ability_id → journey）。
归属不到的任务与决策原样输出，语义归属是调用方（AI）的职责。
输出：stdout 一个 JSON。
"""
import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

BRAIN = "http://localhost:5221/api/brain"
TZ = ZoneInfo("Asia/Shanghai")
EXCLUDE_NAME_PATTERNS = ("[smoke]", "[v1]", "gp-agg-smoke")


def get(path):
    with urllib.request.urlopen(f"{BRAIN}{path}", timeout=30) as r:
        return json.loads(r.read())


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return None


def windows(period, base: date):
    """返回 (当前窗口起, 当前窗口止, 上一窗口起, 上一窗口止)，Asia/Shanghai 自然日/周/月。"""
    def dt(d):
        return datetime(d.year, d.month, d.day, tzinfo=TZ)

    if period == "daily":
        cur_s = dt(base)
        return cur_s, cur_s + timedelta(days=1), cur_s - timedelta(days=1), cur_s
    if period == "weekly":
        cur_s = dt(base - timedelta(days=base.weekday()))
        return cur_s, cur_s + timedelta(days=7), cur_s - timedelta(days=7), cur_s
    if period == "monthly":
        cur_s = dt(base.replace(day=1))
        nxt = (base.replace(day=28) + timedelta(days=4)).replace(day=1)
        prev_month_end = base.replace(day=1) - timedelta(days=1)
        return cur_s, dt(nxt), dt(prev_month_end.replace(day=1)), cur_s
    raise ValueError(f"未知 period: {period}")


def active_lines(only_names):
    lines = {}
    for j in get("/journeys"):
        name = j.get("name") or ""
        if j.get("status") == "deprecated":
            continue
        if any(p in name for p in EXCLUDE_NAME_PATTERNS):
            continue
        if only_names and name not in only_names:
            continue
        # 同名 journey 取最后一条，去重
        lines[name] = {"journey_id": j["id"], "name": name, "maturity": j.get("maturity")}
    return {v["journey_id"]: v for v in lines.values()}


def ability_to_journey():
    mapping = {}
    try:
        for f in get("/journey_features?limit=500"):
            if f.get("id") and f.get("journey_id"):
                mapping[f["id"]] = f["journey_id"]
    except Exception as e:
        print(f"警告：journey_features 拉取失败，ability 归属不可用：{e}", file=sys.stderr)
    return mapping


def fetch_tasks(prev_s):
    """不带 status 的列表 API 缺全字段且截断在旧数据；带 status= 的列表返回全字段、
    按 updated_at 降序。分 status 拉，limit=500 对日/周窗口足够；截断则告警。"""
    tasks = []
    for st in ("completed", "completed_no_pr", "in_progress"):
        rows = get(f"/tasks?status={st}&limit=500")
        rows = rows if isinstance(rows, list) else rows.get("tasks", [])
        tasks.extend(rows)
        if len(rows) >= 500:
            oldest = parse_ts(rows[-1].get("updated_at"))
            if oldest and oldest > prev_s:
                print(f"警告：status={st} 拉满 500 条仍未覆盖到窗口起点，"
                      f"该 status 计数可能偏低（最旧 updated_at={oldest.isoformat()}）",
                      file=sys.stderr)
    return tasks


def task_done_ts(t):
    """完成时间：completed_at 优先；大量任务没盖章（数据卫生债），
    status 为 completed* 时用 updated_at 兜底并打标。返回 (ts, is_fallback)。"""
    ts = parse_ts(t.get("completed_at"))
    if ts:
        return ts, False
    if str(t.get("status", "")).startswith("completed"):
        return parse_ts(t.get("updated_at")), True
    return None, False


def task_journey(task, a2j):
    payload = task.get("payload") or {}
    jid = payload.get("journey_id") or task.get("journey_id")
    if jid:
        return jid
    aid = task.get("ability_id")
    return a2j.get(aid) if aid else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", choices=["daily", "weekly", "monthly"], default="daily")
    ap.add_argument("--lines", default="", help="journey 名称，逗号分隔；空=全部活跃 Line")
    ap.add_argument("--date", default="", help="报告基准日 YYYY-MM-DD，默认今天(Asia/Shanghai)")
    args = ap.parse_args()

    base = date.fromisoformat(args.date) if args.date else datetime.now(TZ).date()
    cur_s, cur_e, prev_s, prev_e = windows(args.period, base)
    only = {s.strip() for s in args.lines.split(",") if s.strip()} or None

    lines = active_lines(only)
    a2j = ability_to_journey()
    tasks = fetch_tasks(prev_s)

    agg = {
        jid: {
            **info,
            "current": {"tasks_completed": 0, "prs_merged": 0, "tasks_in_progress": 0,
                        "completed_task_titles": [], "fallback_ts_count": 0},
            "previous": {"tasks_completed": 0, "prs_merged": 0},
        }
        for jid, info in lines.items()
    }
    unattributed = []

    for t in tasks:
        jid = task_journey(t, a2j)
        bucket = agg.get(jid)
        done, fallback = task_done_ts(t)
        merged = parse_ts(t.get("pr_merged_at"))

        if bucket is None:
            if done and cur_s <= done < cur_e:
                unattributed.append({"id": t["id"], "title": t.get("title"),
                                     "completed_at": t.get("completed_at"),
                                     "ts_fallback": fallback,
                                     "task_type": t.get("task_type")})
            continue
        if done and cur_s <= done < cur_e:
            bucket["current"]["tasks_completed"] += 1
            bucket["current"]["completed_task_titles"].append(t.get("title"))
            if fallback:
                bucket["current"]["fallback_ts_count"] += 1
        elif done and prev_s <= done < prev_e:
            bucket["previous"]["tasks_completed"] += 1
        if merged and cur_s <= merged < cur_e:
            bucket["current"]["prs_merged"] += 1
        elif merged and prev_s <= merged < prev_e:
            bucket["previous"]["prs_merged"] += 1
        if t.get("status") == "in_progress":
            bucket["current"]["tasks_in_progress"] += 1

    dec_cur, dec_prev = [], 0
    for d in get("/decisions?limit=300"):
        if d.get("status") != "active":
            continue
        ts = parse_ts(d.get("created_at"))
        if ts and cur_s <= ts < cur_e:
            dec_cur.append({"id": d["id"], "topic": d.get("topic"),
                            "summary": (d.get("decision") or "")[:120],
                            "attributed_line": None})
        elif ts and prev_s <= ts < prev_e:
            dec_prev += 1

    print(json.dumps({
        "period": args.period,
        "generated_at": datetime.now(TZ).isoformat(),
        "current_window": [cur_s.isoformat(), cur_e.isoformat()],
        "previous_window": [prev_s.isoformat(), prev_e.isoformat()],
        "lines": sorted(agg.values(), key=lambda x: -x["current"]["tasks_completed"]),
        "decisions": {"current": dec_cur, "previous_count": dec_prev},
        "unattributed_tasks": unattributed,
        "tasks_fetched": len(tasks),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```
