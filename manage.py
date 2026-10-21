#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manage.py — TNE-Core 独立发布管理入口（一键自主运维 GitHub）
================================================================
用法（在项目目录）：
  python manage.py status                       # 仓库/本地状态
  python manage.py push "<提交信息>"             # add-commit-push 到 GitHub
  python manage.py topics                        # 查看 topics
  python manage.py topics --set a,b,c            # 设置 topics
  python manage.py describe "<新描述>"           # 更新仓库描述
  python manage.py release <tag> "<标题>" "<正文>"  # 打 tag + 创建 GitHub Release
  python manage.py sync "<提交信息>"             # push + 同步

凭据：从 git credential store 读取 GitHub token（见 .git-credentials，权限600），
无需每次手动输入；token 不在本脚本与命令行中明文出现。
"""
import re
import os
import sys
import json
import subprocess
import urllib.request

REPO = "q1z2q3-debug/trinary-19683"
CRED_FILE = "/home/user/.doubao/agent_mode/workspace/.git-credentials"
DEFAULT_TOPICS = [
    "trinary", "ternary", "19683", "cognitive-system", "deterministic",
    "symbolic", "llm", "agent", "cognition", "falsification",
    "reasoning", "chinese", "python", "knowledge-graph", "open-source",
]


def get_token():
    try:
        for line in open(CRED_FILE):
            m = re.match(r"https://[^:]+:([^@]+)@github\.com", line.strip())
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def api(method, path, body=None):
    tok = get_token()
    if not tok:
        print("未找到 GitHub 凭据"); return None
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except Exception as e:
        print("API 错误:", e)
        return None


def git(args):
    return subprocess.run(["git"] + args, capture_output=True, text=True)


def cmd_status():
    info = api("GET", "/repos/" + REPO)
    if info:
        print(f"仓库: {info['full_name']} | stars: {info['stargazers_count']}"
              f" | forks: {info['forks_count']} | 默认分支: {info['default_branch']}")
        print(f"描述: {info.get('description')}")
        print(f"topics({len(info.get('topics', []))}): {info.get('topics')}")
    r = git(["log", "-1", "--oneline"]); print("HEAD:", r.stdout.strip())
    r = git(["status", "--short"])
    print("本地改动:", "\n" + r.stdout if r.stdout.strip() else "  (clean)")


def cmd_push(msg):
    git(["add", "-A"])
    st = git(["status", "--short"]).stdout.strip()
    if not st:
        print("无改动可提交"); return
    r = git(["commit", "-m", msg])
    print(r.stdout or r.stderr)
    r = git(["push"])
    print("push:", (r.stdout or r.stderr).strip())


def cmd_topics(setv=None):
    if setv:
        names = [x.strip() for x in setv.split(",") if x.strip()]
        r = api("PUT", "/repos/" + REPO + "/topics", {"names": names})
        print("topics 已设:", r.get("names") if r else "失败")
    else:
        info = api("GET", "/repos/" + REPO)
        print("当前 topics:", info.get("topics") if info else "—")


def cmd_describe(text):
    r = api("PATCH", "/repos/" + REPO, {"description": text})
    print("描述已更新:", r.get("description") if r else "失败")


def cmd_release(tag, title, body=""):
    git(["tag", tag]); r = git(["push", "origin", tag])
    print("tag push:", (r.stdout or r.stderr).strip())
    r = api("POST", f"/repos/{REPO}/releases",
            {"tag_name": tag, "name": title, "body": body})
    print("Release:", r.get("html_url") if r else "失败")


def cmd_sync(msg):
    cmd_push(msg)
    cmd_topics()
    print("sync 完成")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    c = sys.argv[1]
    if c == "status":
        cmd_status()
    elif c == "push" and len(sys.argv) > 2:
        cmd_push(sys.argv[2])
    elif c == "topics":
        setv = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else None
        cmd_topics(setv)
    elif c == "describe" and len(sys.argv) > 2:
        cmd_describe(sys.argv[2])
    elif c == "release" and len(sys.argv) > 3:
        cmd_release(sys.argv[2], sys.argv[3],
                    sys.argv[4] if len(sys.argv) > 4 else "")
    elif c == "sync" and len(sys.argv) > 2:
        cmd_sync(sys.argv[2])
    else:
        print("用法见文件头文档")
