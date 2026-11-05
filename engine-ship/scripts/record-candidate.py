#!/usr/bin/env python3
"""只记录同一PR/head的候选交付；PR终态留给watchdog。"""
import argparse
import datetime
import hashlib
import json
import os
import tempfile
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


class Unknown(Exception):
    pass


def loaded_source(value):
    loaded = Path(value)
    if not loaded.is_absolute():
        raise Unknown('需要实际加载Skill的绝对路径')
    skill = loaded.resolve(strict=True)
    helper = skill.parent / 'scripts/record-candidate.py'
    if (skill.name != 'SKILL.md' or skill.parent.name != 'engine-ship'
            or helper.resolve(strict=True) != Path(__file__).resolve(strict=True)
            or helper.resolve(strict=True) != helper):
        raise Unknown('不是本次加载Skill的同physical release helper')
    parts = skill.read_text(encoding='utf-8').split('---', 2)
    if (len(parts) != 3 or parts[0].strip()
            or re.findall(r'^name:\s*(.+?)\s*$', parts[1], re.M) != ['engine-ship']
            or re.findall(r'^version:\s*(.+?)\s*$', parts[1], re.M) != ['17.0.0']):
        raise Unknown('实际Skill身份或版本不符')


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise Unknown('只读命令失败，不能确认候选身份')
    return result.stdout.strip()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args):
        raise Unknown('Brain请求不接受重定向')


def brain_client(base):
    url = urllib.parse.urlsplit(base)
    if (url.scheme != 'http' or url.hostname not in ('localhost', '127.0.0.1')
            or not url.port or url.username or url.password or url.path not in ('', '/')
            or url.query or url.fragment):
        raise Unknown('Brain地址必须是本机明确端口的API根地址')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    def request(task_id, body=None):
        req = urllib.request.Request(base.rstrip('/') + '/api/brain/tasks/' + task_id,
            data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json'}, method='GET' if body is None else 'PATCH')
        with opener.open(req, timeout=5) as response:
            if response.status != 200:
                raise Unknown('Brain未返回确认响应')
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise Unknown('Brain响应超过边界')
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise Unknown('Brain响应身份缺失')
            return value
    return request


def validate_evidence(items):
    required = {'path', 'sha256', 'command', 'result'}
    for item in items:
        if (not required.issubset(item)
                or any(not isinstance(item[key], str) or not item[key].strip() for key in required)
                or not re.fullmatch(r'[0-9a-fA-F]{64}', item['sha256'])):
            raise Unknown('证据必须有location/hash/真实command与result')
        location = item['path']
        if location.startswith('https://'):
            url = urllib.parse.urlsplit(location)
            if (not url.hostname or url.username or url.password
                    or (url.port is not None and url.port < 1)
                    or any(c.isspace() for c in location)):
                raise Unknown('HTTPS证据引用结构无效')
            # 只确认引用结构；不下载、不声称URL的远端产物或业务效果已经验收。
            continue
        artifact = Path(location)
        if not artifact.is_absolute() or not artifact.is_file():
            raise Unknown('本地证据必须是存在的绝对文件路径')
        digest = hashlib.sha256()
        with artifact.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != item['sha256'].lower():
            raise Unknown('本地产物实际SHA256不符')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('loaded-skill', 'task-id', 'repo', 'pr', 'head', 'actor', 'facts-file', 'dev-mode'):
        parser.add_argument('--' + field, required=True)
    parser.add_argument('--brain-url', default='http://localhost:5221')
    args = parser.parse_args()
    loaded_source(args.loaded_skill)
    if str(uuid.UUID(args.task_id)) != args.task_id:
        raise Unknown('Task UUID不规范')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo):
        raise Unknown('repo必须明确owner/repo')
    if not re.fullmatch(r'[1-9][0-9]*', args.pr) or not re.fullmatch(r'[0-9a-f]{40}', args.head):
        raise Unknown('需要真实PR号及完整Git HEAD')
    if not args.actor.strip() or len(args.actor) > 200:
        raise Unknown('缺执行者actor')
    facts_path = Path(args.facts_file)
    if not facts_path.is_absolute():
        raise Unknown('事实证据文件必须绝对路径')
    evidence = json.loads(facts_path.read_text(encoding='utf-8'))
    if (not isinstance(evidence, dict) or set(evidence) != {'facts', 'evidence'}
            or not isinstance(evidence['facts'], list) or not evidence['facts']
            or any(not isinstance(x, str) or not x.strip() for x in evidence['facts'])
            or not isinstance(evidence['evidence'], list) or not evidence['evidence']
            or any(not isinstance(x, dict) or not x for x in evidence['evidence'])):
        raise Unknown('必须提供具体事实与证据引用')
    validate_evidence(evidence['evidence'])
    supplied_mode = Path(args.dev_mode)
    if not supplied_mode.is_absolute() or supplied_mode.is_symlink():
        raise Unknown('dev-mode必须是本仓绝对路径且不是文件软链')
    mode = supplied_mode.resolve(strict=True)
    if (not mode.is_file()
            or mode.parent != Path.cwd().resolve()
            or not re.fullmatch(r'\.dev-mode(?:\.[A-Za-z0-9_.-]+)?', mode.name)):
        raise Unknown('需要本候选工作树真实dev-mode文件')
    mode_bytes = mode.read_bytes()
    mode_text = mode_bytes.decode('utf-8')
    if (re.findall(r'^task_id:\s*(.+?)\s*$', mode_text, re.M) != [args.task_id]
            or re.findall(r'^step_4_ship:\s*(.+?)\s*$', mode_text, re.M) not in (['pending'], ['done'])):
        raise Unknown('dev-mode的Task或ship候选阶段身份不符')
    request = brain_client(args.brain_url)
    if command(['git', 'rev-parse', 'HEAD']) != args.head or command(['git', 'status', '--porcelain']):
        raise Unknown('当前Git候选HEAD不符或工作树未提交')
    pr = json.loads(command(['gh', 'pr', 'view', args.pr, '--repo', args.repo,
        '--json', 'number,url,headRefOid,state']))
    url = 'https://github.com/' + args.repo + '/pull/' + args.pr
    if (not isinstance(pr, dict) or pr.get('number') != int(args.pr) or pr.get('url') != url
            or pr.get('headRefOid') != args.head or pr.get('state') != 'OPEN'):
        raise Unknown('PR身份/head不符或不是OPEN；由watchdog验终态')
    before = request(args.task_id)
    if (before.get('id') != args.task_id or before.get('status') != 'in_progress'
            or not isinstance(before.get('result'), (dict, type(None)))):
        raise Unknown('Task身份/进行中状态无法确认')
    candidate = {'schema_version': 1, 'stage': 'candidate', 'actor': args.actor,
        'task_id': args.task_id, 'repo': args.repo, 'pr_url': url, 'pr_number': int(args.pr),
        'head_sha': args.head, 'pr_state': 'OPEN', 'merged': False,
        'facts': evidence['facts'], 'evidence': evidence['evidence'],
        'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    # 当前Brain PATCH result为顶层jsonb合并：只写本人ship_candidate，不回送旧result覆盖并发键。
    request(args.task_id, {'result': {'ship_candidate': candidate}})
    after = request(args.task_id)
    if (after.get('id') != args.task_id or after.get('status') != 'in_progress'
            or not isinstance(after.get('result'), dict)
            or after['result'].get('ship_candidate') != candidate):
        raise Unknown('候选回执读回不一致，不能报告交付')
    if mode.read_bytes() != mode_bytes:
        raise Unknown('dev-mode并发改变，未标候选done')
    updated = re.sub(r'^step_4_ship:\s*pending[ \t]*$', 'step_4_ship: done', mode_text, flags=re.M)
    if updated != mode_text:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=mode.parent,
                    prefix='.ship-candidate-', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(updated)
            os.chmod(temporary, mode.stat().st_mode & 0o777)
            os.replace(temporary, mode)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    print('CANDIDATE_RECORDED: Task事实与证据已读回；尚未合并，继续watchdog')


if __name__ == '__main__':
    try:
        main()
    except (Unknown, OSError, ValueError, TypeError, subprocess.SubprocessError, urllib.error.URLError):
        # 不输出原HTTP body/子进程输出/事实正文，以免把敏感上下文带进日志。
        print('SHIP_UNKNOWN: 候选交付未确认；保留工作树和Task进行中，交watchdog核对', file=sys.stderr)
        sys.exit(12)
