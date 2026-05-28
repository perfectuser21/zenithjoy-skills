#!/usr/bin/env python3
"""
After skill-creator creates or updates a skill, run this to:
1. Sync to Notion Skill Registry
2. Sync to Brain DB skill_registry
3. Print a summary with timestamp + eval score

Usage:
  python3 sync-skill-to-notion.py \
    --name "my-skill" \
    --description "One-line description from frontmatter" \
    --action "created|updated" \
    [--eval-score "8/10 (80%)"] \
    [--eval-file "/path/to/grading.json"]
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

SKILL_REGISTRY_DB = "353c40c2-ba63-81bf-ae3e-f0e6fa3753d7"
BRAIN_API = "http://localhost:5221"


def load_notion_key():
    env_file = os.path.expanduser("~/.credentials/notion.env")
    if not os.path.exists(env_file):
        sys.exit("ERROR: ~/.credentials/notion.env not found. Run notion credential sync first.")
    key = None
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("NOTION_API_KEY="):
                key = line.split("=", 1)[1]
                break
    if not key:
        sys.exit("ERROR: NOTION_API_KEY not found in ~/.credentials/notion.env")
    return key


def notion_request(method, path, body=None, api_key=None):
    url = f"https://api.notion.com/v1{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f"  Notion API error {e.code}: {err.get('message', str(err))}")
        return None


def brain_request(method, path, body=None):
    url = f"{BRAIN_API}{path}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  Brain API unavailable: {e}")
        return None


def parse_eval_file(path):
    """Extract pass rate from grading.json produced by skill-creator evals."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        # grading.json structure: list of {pass: bool, score: float, ...}
        if isinstance(data, list):
            total = len(data)
            passed = sum(1 for r in data if r.get("pass") or r.get("score", 0) >= 0.5)
            return f"{passed}/{total} ({int(passed/total*100)}%)" if total else None
        # summary format: {pass_rate: 0.8, ...}
        if isinstance(data, dict) and "pass_rate" in data:
            rate = data["pass_rate"]
            return f"{int(rate*100)}%"
    except Exception:
        pass
    return None


def find_existing_notion_page(skill_name, api_key):
    """Look for an existing Skill Registry page with this name."""
    body = {
        "filter": {
            "property": "Name",
            "title": {"equals": skill_name}
        }
    }
    result = notion_request("POST", f"/databases/{SKILL_REGISTRY_DB}/query", body, api_key)
    if result and result.get("results"):
        return result["results"][0]["id"]
    return None


def sync_to_notion(name, description, action, eval_score, api_key):
    now = datetime.now(timezone.utc).isoformat()
    now_display = datetime.now().strftime("%Y-%m-%d %H:%M")

    action_label = "新建" if action == "created" else "更新"
    eval_text = eval_score if eval_score else "（未跑 eval）"

    # Try to find existing page first
    existing_id = find_existing_notion_page(name, api_key)

    # Determine status select value
    properties = {
        "Name": {"title": [{"text": {"content": name}}]},
        "Description": {"rich_text": [{"text": {"content": description or ""}}]},
        "Status": {"select": {"name": "active"}},
        "Source": {"select": {"name": "skill-creator"}},
    }

    children = [
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"text": {"content": f"{action_label}记录"}}]}},
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": f"操作：{action_label}"}}]}},
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": f"时间：{now_display}"}}]}},
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": f"Eval 结果：{eval_text}"}}]}},
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [{"text": {"content": f"安装路径：~/.claude/skills/{name}/"}}]}},
    ]

    if existing_id:
        # Update existing page properties
        result = notion_request("PATCH", f"/pages/{existing_id}", {"properties": properties}, api_key)
        if result:
            # Append new log block to existing page
            notion_request("PATCH", f"/blocks/{existing_id}/children", {"children": children}, api_key)
            return existing_id, False
    else:
        # Create new page
        body = {
            "parent": {"database_id": SKILL_REGISTRY_DB},
            "properties": properties,
            "children": children,
        }
        result = notion_request("POST", "/pages", body, api_key)
        if result:
            return result["id"], True
    return None, None


def sync_to_brain(name, description, eval_score, action):
    """Sync to Brain DB skill_registry via Brain API."""
    # Check if skill already exists
    existing = brain_request("GET", f"/api/brain/skills?name={urllib.parse.quote(name)}&limit=5")

    payload = {
        "name": name,
        "description": description or "",
        "status": "active",
        "category": "skill-creator-managed",
        "metadata": {
            "eval_score": eval_score or "not run",
            "last_action": action,
            "last_updated": datetime.now().isoformat(),
        }
    }

    # Brain API returns a list directly
    existing_list = existing if isinstance(existing, list) else (existing.get("skills") or existing.get("data") or [])
    if existing_list:
        skill_id = existing_list[0]["id"]
        result = brain_request("PATCH", f"/api/brain/skills/{skill_id}", payload)
        return "updated"
    else:
        result = brain_request("POST", "/api/brain/skills", payload)
        return "created"


def main():
    import urllib.parse  # noqa: needed for brain sync

    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--action", default="created", choices=["created", "updated"])
    parser.add_argument("--eval-score", default="")
    parser.add_argument("--eval-file", default="")
    args = parser.parse_args()

    # Parse eval score from file if not provided directly
    eval_score = args.eval_score
    if not eval_score and args.eval_file:
        eval_score = parse_eval_file(args.eval_file) or ""

    print(f"\n{'='*50}")
    print(f"  Skill: {args.name}")
    print(f"  Action: {args.action}")
    print(f"  Eval: {eval_score or '（未跑）'}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    api_key = load_notion_key()

    print("\n[1/2] Syncing to Notion Skill Registry...")
    page_id, created = sync_to_notion(args.name, args.description, args.action, eval_score, api_key)
    if page_id:
        action_word = "新建" if created else "更新"
        notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"
        print(f"  ✅ {action_word} Notion page: {notion_url}")
    else:
        print("  ⚠️  Notion sync failed (check token)")

    print("\n[2/2] Syncing to Brain DB skill_registry...")
    brain_action = sync_to_brain(args.name, args.description, eval_score, args.action)
    print(f"  ✅ Brain DB {brain_action}: {args.name}")

    print(f"\n✅ Done — {args.name} ({args.action}) 已记录\n")


if __name__ == "__main__":
    import urllib.parse
    main()
