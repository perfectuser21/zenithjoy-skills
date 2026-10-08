#!/usr/bin/env python3
"""连续通过计数：数一个阶段任务下「同一版本、不同输入、连续通过」了几次。

规则（决策 5826ddd7 / 6ec463c3 / 1b469079），从最新一次往前数：
  - 还没核验的运行：待核验，不计数也不打断；
  - 缺 skill 版本或输入的运行：无法核对，不计数也不打断；
  - skill 版本或处置表片指纹与最新一次不同：到此为止（改版即清零）；
  - 通过：+1；输入与已计入的重复则不计；
  - 失败且核验写明外部原因：作废，不计数也不清零；
  - 其他失败：到此为止（清零）。

一次运行 = 一张执行单（正文【执行参数】里写「计数阶段任务：<阶段任务 id>」，或挂在阶段任务下）；
一次判定 = 一张 audit 任务（payload.source_task_id 指回执行单，result.verification 是 run-verify 的 JSON）。
skill 版本、输入、处置表片指纹以执行单【执行参数】为准，缺了才用核验 JSON 里的同名字段。

用法：python3 count_streak.py --stage-task <阶段任务 id> [--k 10] [--brain http://100.79.41.61:5221]
只读：只发 GET，不改任何东西。输出一行 JSON。
"""
import argparse
import json
import os
import re
import sys
import urllib.request

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


def collect_runs(brain, stage_id):
    """找执行单：先看挂在阶段任务下的子任务，再补正文里写了「计数阶段任务：<id>」的秋米任务。"""
    runs = {}
    try:
        chain = _get(brain, "/tasks/%s/chain" % stage_id) or {}
        for t in chain.get("children") or chain.get("tasks") or []:
            if t.get("task_type") != "audit" and t.get("id") != stage_id:
                runs[t["id"]] = t
    except Exception:
        pass
    for t in _task_list(_get(brain, "/tasks?task_type=qiumi_task&limit=500")):
        if parse_params(_body(t)).get("计数阶段任务") == stage_id:
            runs[t["id"]] = t

    audits = {}
    for a in _task_list(_get(brain, "/tasks?task_type=audit&limit=500")):
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
    ap.add_argument("--brain", default=os.environ.get("BRAIN_URL", "http://100.79.41.61:5221"))
    args = ap.parse_args(argv)

    k = args.k
    if k is None:
        try:
            stage = _get(args.brain, "/tasks/%s" % args.stage_task) or {}
            k = int(parse_params(_body(stage)).get("K") or 10)
        except Exception:
            k = 10
    runs = collect_runs(args.brain, args.stage_task)
    res = count_streak(runs, k)
    res["stage_task"] = args.stage_task
    res["runs_seen"] = len(runs)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
