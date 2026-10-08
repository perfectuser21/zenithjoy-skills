#!/usr/bin/env python3
"""连续通过计数：数一个阶段任务下「同一版本、不同输入、连续通过」了几次。

规则（决策 5826ddd7 / 6ec463c3 / 1b469079），从最新一次往前数：
  - 还没核验的运行：待核验，不计数也不打断；
  - 缺 skill 版本或输入的运行：无法核对，不计数也不打断；
  - skill 版本或处置表片指纹与最新一次不同：到此为止（改版即清零）；
  - 通过：+1；输入与已计入的重复则不计；
  - 失败且核验写明外部原因：作废，不计数也不清零；
  - 其他失败：到此为止（清零）。

一次运行 = 一张执行单，一次判定 = 一张 audit 任务（payload.source_task_id 指回执行单，
result.verification 是 run-verify 的 JSON）。两张都必须挂在阶段任务下（建单时带 parent_task_id）。
skill 版本、输入、处置表片指纹以执行单【执行参数】为准，缺了才用核验 JSON 里的同名字段。

为什么不全量扫描：跑场机到 Brain 的链路很慢（实测 xian-m1 拉 500 条审计单 1.25 MB 要 88 秒），
所以默认只走 /tasks/<阶段任务>/chain 拿子任务列表，再并行逐张 GET（单张约 0.5～1 秒）。
--scan 额外按 task_type 全量拉取，补找正文写了「计数阶段任务：<id>」但没挂父任务的老记录，很慢，只在必要时用。

用法：python3 count_streak.py --stage-task <阶段任务 id> [--k 10] [--scan] [--brain http://100.79.41.61:5221]
只读：只发 GET，不改任何东西。输出一行 JSON。
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PARAM_BLOCK = re.compile(r"【执行参数】(.*?)(?:【执行参数结束】|\Z)", re.S)
PARAM_LINE = re.compile(r"^\s*([^:：\n]+?)\s*[:：]\s*(.*?)\s*$")


def parse_params(body):
    """取正文【执行参数】块里的「键：值」行；键 Skill / skill 统一成 skill。"""
    m = PARAM_BLOCK.search(body or "")
    out = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        lm = PARAM_LINE.match(line)
        if not lm:
            continue
        key, val = lm.group(1).strip(), lm.group(2).strip()
        if key.lower() == "skill":
            key = "skill"
        out[key] = val
    return out


def count_streak(runs, k):
    """runs 按时间从旧到新；每项含 id / skill / slice_digest / input / verdict / external_cause。"""
    result = {"k": k, "streak": 0, "reached": False, "current": None, "counted": [], "voided": [],
              "pending": [], "unverifiable": [], "duplicate_input": [], "reset_by": None}
    newest_first = list(reversed(runs))
    for r in newest_first:
        if r.get("skill"):
            result["current"] = {"skill": r["skill"], "slice_digest": r.get("slice_digest")}
            break
    if result["current"] is None:
        result["pending"] = [r["id"] for r in newest_first if r.get("verdict") is None]
        return result

    cur_skill = result["current"]["skill"]
    cur_slice = result["current"]["slice_digest"]
    seen_inputs = set()
    for r in newest_first:
        if r.get("verdict") is None:
            result["pending"].append(r["id"])
            continue
        if not r.get("skill") or not r.get("input"):
            result["unverifiable"].append(r["id"])
            continue
        if r["skill"] != cur_skill:
            result["reset_by"] = {"run": r["id"], "reason": "版本变了：%s → %s" % (r["skill"], cur_skill)}
            break
        if r.get("slice_digest") != cur_slice:
            result["reset_by"] = {"run": r["id"], "reason": "处置表片指纹变了：%s → %s" % (r.get("slice_digest"), cur_slice)}
            break
        if r["verdict"] == "pass":
            if r["input"] in seen_inputs:
                result["duplicate_input"].append(r["id"])
                continue
            seen_inputs.add(r["input"])
            result["counted"].append(r["id"])
            continue
        if r.get("external_cause"):
            result["voided"].append(r["id"])
            continue
        result["reset_by"] = {"run": r["id"], "reason": "失败（非外部原因）"}
        break

    result["streak"] = len(result["counted"])
    result["reached"] = result["streak"] >= k
    return result


def _get(brain, path):
    with urllib.request.urlopen(brain.rstrip("/") + "/api/brain" + path, timeout=30) as resp:
        return json.loads(resp.read() or b"null")


def _task_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("tasks") or data.get("data") or []
    return []


def _body(task):
    payload = task.get("payload") or {}
    src = payload.get("qiumi_source") or {}
    return src.get("body") or task.get("description") or ""


def collect_runs(get, stage_id, scan=False):
    """get(path) 返回 Brain /api/brain 下某路径的 JSON。

    默认：chain 拿阶段任务的子任务 → 并行逐张取全量 → 非 audit 为执行单，audit 按 source_task_id 配对。
    scan=True：再全量拉取秋米任务与审计单，补找没挂父任务、但正文写了「计数阶段任务」的老记录。
    chain 读不到时抛异常，不当作「零次」。
    """
    chain = get("/tasks/%s/chain" % stage_id) or {}
    child_ids = [c["id"] for c in (chain.get("children") or []) if c.get("id") and c.get("id") != stage_id]
    with ThreadPoolExecutor(max_workers=8) as pool:
        children = list(pool.map(lambda tid: get("/tasks/%s" % tid), child_ids))

    runs, audit_list = {}, []
    for t in children:
        if not t:
            continue
        if t.get("task_type") == "audit":
            audit_list.append(t)
        else:
            runs[t["id"]] = t
    if scan:
        for t in _task_list(get("/tasks?task_type=qiumi_task&limit=500")):
            if parse_params(_body(t)).get("计数阶段任务") == stage_id:
                runs.setdefault(t["id"], t)
        audit_list += _task_list(get("/tasks?task_type=audit&limit=500"))

    audits = {}
    for a in audit_list:
        src = (a.get("payload") or {}).get("source_task_id")
        if src in runs and (src not in audits or a.get("created_at", "") > audits[src].get("created_at", "")):
            audits[src] = a

    out = []
    for tid, t in runs.items():
        p = parse_params(_body(t))
        v = ((audits.get(tid) or {}).get("result") or {}).get("verification") or {}
        out.append({
            "id": tid,
            "created_at": t.get("created_at", ""),
            "skill": p.get("skill") or v.get("skill"),
            "slice_digest": p.get("处置表片指纹") or v.get("slice_digest"),
            "input": p.get("输入") or v.get("input"),
            "verdict": v.get("verdict") if tid in audits else None,
            "external_cause": v.get("external_cause"),
        })
    out.sort(key=lambda r: r["created_at"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="连续通过计数（只读）")
    ap.add_argument("--stage-task", required=True, help="阶段任务 id（验证 / 沉淀后重跑）")
    ap.add_argument("--k", type=int, default=None, help="达标次数；不给则读阶段任务【执行参数】的 K，再不行默认 10")
    ap.add_argument("--scan", action="store_true", help="额外全量扫描补找没挂父任务的老记录（跑场机上很慢）")
    ap.add_argument("--brain", default=os.environ.get("BRAIN_URL", "http://100.79.41.61:5221"))
    args = ap.parse_args(argv)

    def get(path):
        return _get(args.brain, path)

    k = args.k
    if k is None:
        try:
            stage = get("/tasks/%s" % args.stage_task) or {}
            k = int(parse_params(_body(stage)).get("K") or 10)
        except Exception:
            k = 10
    try:
        runs = collect_runs(get, args.stage_task, scan=args.scan)
    except Exception as e:
        print(json.dumps({"stage_task": args.stage_task, "error": "读不到 Brain：%s" % e}, ensure_ascii=False))
        return 2
    res = count_streak(runs, k)
    res["stage_task"] = args.stage_task
    res["runs_seen"] = len(runs)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
