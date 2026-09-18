#!/usr/bin/env python3
"""Live dashboard of every Claude Code session running on this machine.

Data sources:
  - `claude agents --json`           -> sessions, pid/cwd/kind/status/waitingFor
  - ~/.claude/projects/*/<sid>.jsonl -> tokens, model, effort, git branch, activity
  - .../<sid>/subagents/agent-*      -> subagent tree (agentType, spawnDepth, tokens)
  - ~/.claude/monitor/notify/*.json  -> Notification hook: session is waiting on the user

Run:  python3 claude_monitor.py [--port 8787] [--open]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
CONFIG = Path.home() / ".claude.json"
NOTIFY = Path.home() / ".claude" / "monitor" / "notify"
SUBAGENT_ACTIVE_SEC = 60

# `claude agents --json` -> waitingFor
WAITING_LABELS = {"input needed": "waiting for your input"}
# Notification hook matchers (see hooks/notification.py)
NOTIFY_LABELS = {
    "permission_prompt": "waiting for tool permission",
    "idle_prompt": "waiting for a prompt",
    "elicitation_dialog": "MCP dialog waiting for input",
}

# Context window sizes (source: claude-api skill). The whole Claude 5 family is
# 1M, Haiku 4.5 only 200K. Careful: the transcript's `message.model` does NOT carry
# the [1m] suffix, so the 1M tier cannot be told apart from the log - hence 1M as
# the default for the 5 family. Claude Code may auto-compact earlier (see
# `claude --autocompact`).
CONTEXT_LIMITS = {
    "claude-haiku-4-5": 200_000,
}
DEFAULT_LIMIT = 1_000_000

# The checking steps of /feature:start - the ones that run as a subagent and so leave a
# trace of their own. The rest of that workflow runs in the main context, where there is
# nothing to read, and the dashboard does not pretend otherwise.
FEATURE_STEPS = [
    ("plan", "feature:plan-reviewer"),
    ("e2e", "feature:e2e-tester"),
    ("lint", "feature:linter"),
    ("review", "feature:reviewer"),
    ("docs", "feature:doc-writer"),
    ("security", "feature:security-reviewer"),
]
# The first line of an agent's report (see plugins/feature/agents/*.md). A verdict that
# did not come back clean earns a `*` on the pill; the word itself is in the tooltip.
VERDICT_RE = re.compile(r"VERDICT:\s*([A-Z]+)")
VERDICT_FLAG = {"CHANGES", "HANDBACK", "FAIL"}

# Fields from ~/.claude.json -> cachedUsageUtilization.utilization.limits
LIMIT_LABELS = {"session": "session (5 h)", "weekly_all": "week, all models",
                "weekly_scoped": "week"}
# the KPI tile is narrow - the long label only survives in the tooltip
SHORT_LABELS = {"session": "5 h", "weekly_all": "week all", "weekly_scoped": "week"}

_cache: dict[str, dict] = {}
_usage: dict = {"mtime": 0.0, "data": None}
_lock = threading.Lock()


def _fresh() -> dict:
    return {
        "offset": 0,
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_write": 0,
        "thinking": 0,
        "turns": 0,
        "context": 0,
        "model": None,
        "effort": None,
        "branch": None,
        "last_ts": None,
        "last_agent": None,
        "feature_run": None,
    }


AGENT_TEXT_MAX = 800


def agent_text(content) -> str:
    """Visible text of an assistant turn - thinking and tool_use blocks skipped."""
    if not isinstance(content, list):
        return ""
    txt = "\n".join(
        b.get("text", "")
        for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    ).strip()
    return (txt[:AGENT_TEXT_MAX] + "\u2026") if len(txt) > AGENT_TEXT_MAX else txt


def iso_epoch(ts: str | None) -> float | None:
    """Transcript timestamps are UTC ISO; subagent files are compared by mtime."""
    try:
        return datetime.fromisoformat((ts or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def scan(path: str) -> dict:
    """Read only the lines added since the last call and update the aggregates."""
    try:
        size = os.stat(path).st_size
    except OSError:
        return _fresh()

    c = _cache.get(path)
    if c is None or size < c["offset"]:  # new file or truncation
        c = _cache[path] = _fresh()
    if size == c["offset"]:
        return c

    with open(path, "rb") as f:
        f.seek(c["offset"])
        data = f.read()
    cut = data.rfind(b"\n")
    if cut == -1:
        return c
    c["offset"] += cut + 1

    for raw in data[:cut].split(b"\n"):
        if not raw:
            continue
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        if e.get("timestamp"):
            c["last_ts"] = e["timestamp"]
        if e.get("gitBranch"):
            c["branch"] = e["gitBranch"]
        if e.get("effort"):
            c["effort"] = e["effort"]
        msg = e.get("message")
        if not isinstance(msg, dict):
            continue
        if e.get("type") == "user":
            # /feature:start leaves this marker in the transcript, so the row can come up
            # with the run itself instead of waiting for the first subagent to be spawned.
            body = msg.get("content")
            if isinstance(body, str) and "<command-name>/feature:start<" in body:
                c["feature_run"] = iso_epoch(e.get("timestamp"))
        if e.get("type") == "assistant":
            # Turns that only think or call tools keep the previous reply. A subagent
            # transcript is all sidechain - its last reply is the report the
            # orchestrator gets, and that is where the verdict is read from.
            said = agent_text(msg.get("content"))
            if said:
                c["last_agent"] = {"text": said, "ts": e.get("timestamp")}
        u = msg.get("usage")
        if not isinstance(u, dict):
            continue
        inp = u.get("input_tokens", 0)
        cr = u.get("cache_read_input_tokens", 0)
        cw = u.get("cache_creation_input_tokens", 0)
        c["input"] += inp
        c["output"] += u.get("output_tokens", 0)
        c["cache_read"] += cr
        c["cache_write"] += cw
        c["thinking"] += (u.get("output_tokens_details") or {}).get("thinking_tokens", 0)
        c["turns"] += 1
        c["context"] = inp + cr + cw  # last turn = current window occupancy
        if msg.get("model"):
            c["model"] = msg["model"]
    return c


def read_notify(session_id: str, mtime: float) -> dict | None:
    """Notification hook record. Valid until the transcript moves past it - once the
    user answers, the transcript gets written to and the record goes stale."""
    try:
        rec = json.loads((NOTIFY / f"{session_id}.json").read_text())
    except (OSError, ValueError):
        return None
    return rec if rec.get("ts", 0) > mtime else None


def attention(session: dict, session_id: str, mtime: float) -> dict | None:
    """Is the session waiting on the user, and why? The Notification hook knows the
    reason more precisely (which tool wants permission); the CLI status works even
    without the hook."""
    rec = read_notify(session_id, mtime)
    if rec:
        kind = rec.get("kind") or "?"
        return {
            "kind": kind,
            "label": NOTIFY_LABELS.get(kind, kind),
            "detail": rec.get("message") or "",
            "since": rec["ts"],
        }
    if session.get("status") == "waiting":
        wf = session.get("waitingFor") or ""
        return {
            "kind": "waiting",
            "label": WAITING_LABELS.get(wf, wf or "waiting for the user"),
            "detail": "",
            "since": mtime,
        }
    return None


def transcript(session_id: str) -> str | None:
    hits = glob.glob(str(PROJECTS / "*" / f"{session_id}.jsonl"))
    return hits[0] if hits else None


def subagents(transcript_path: str, session_id: str) -> list[dict]:
    d = Path(transcript_path).parent / session_id / "subagents"
    if not d.is_dir():
        return []
    now = time.time()
    out = []
    for meta_path in d.glob("agent-*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        jsonl = str(meta_path).replace(".meta.json", ".jsonl")
        t = scan(jsonl) if os.path.exists(jsonl) else _fresh()
        try:
            mtime = os.stat(jsonl).st_mtime
        except OSError:
            mtime = meta_path.stat().st_mtime
        said = (t["last_agent"] or {}).get("text") or ""
        m = VERDICT_RE.search(said)
        out.append(
            {
                "id": meta_path.name[len("agent-") : -len(".meta.json")],
                "type": meta.get("agentType") or "?",
                "verdict": m.group(1) if m else None,
                "desc": meta.get("description") or "",
                "depth": meta.get("spawnDepth", 1),
                "model": t["model"],
                "turns": t["turns"],
                "tokens": {k: t[k] for k in ("input", "output", "cache_read", "cache_write")},
                "mtime": mtime,
                "active": now - mtime < SUBAGENT_ACTIVE_SEC,
            }
        )
    out.sort(key=lambda a: a["mtime"], reverse=True)
    return out


def feature_steps(
    subs: list[dict], main_busy: bool, run_since: float | None
) -> list[dict] | None:
    """The checking steps of /feature:start, summed up out of the subagent tree: which
    ran, how often, and with what verdict. Repetition is `review x2` - the steps are a
    fixed row and the attempts live inside one, never an arrow back. Nothing is written
    anywhere for this; a step nobody ran is simply shown as not run.

    `run_since` is when /feature:start was last typed, read off the marker the command
    leaves in the transcript. It does two things: the row comes up with the run itself
    (the first steps have no subagent of their own), and a second feature in the same
    session - `/clear` keeps the session id - starts from an empty row instead of
    inheriting the agents of the one before it."""
    runs: dict[str, list[dict]] = {t: [] for _, t in FEATURE_STEPS}
    for a in subs:
        if a["type"] in runs and not (run_since and a["mtime"] < run_since):
            runs[a["type"]].append(a)
    if not run_since and not any(runs.values()):
        return None
    out = []
    for label, agent_type in FEATURE_STEPS:
        got = sorted(runs[agent_type], key=lambda a: a["mtime"])
        last = got[-1] if got else None
        out.append(
            {
                "label": label,
                "state": "running" if last and last["active"] else "done" if got else "unrun",
                "attempts": len(got),
                "verdict": last["verdict"] if last else None,
                "flag": bool(last and last["verdict"] in VERDICT_FLAG),
                "mtime": last["mtime"] if last else None,
            }
        )

    # Two steps have no agent to stand for them - but the order of the workflow does, and
    # that order is fixed. Implementation starts once the plan has been reviewed; fixing
    # findings starts once the review is back. Either is over the moment a step that comes
    # after it runs - e2e does not run before the implementation, docs not before the fixes.
    # The one thing this gets wrong is the minute or two between the plan review and the
    # gate, where the main context is still folding findings into the plan and `impl`
    # already says implementation.
    ran = {st["label"]: st["attempts"] for st in out}

    def derived(label: str, starts_after: str, ends_with: list[str]) -> dict:
        return {
            "label": label,
            "state": "done" if any(ran[b] for b in ends_with)
            else "running" if ran[starts_after] and main_busy
            else "unrun",
            "attempts": 0,
            "verdict": None,
            "flag": False,
            "mtime": None,
        }

    out.append(derived("impl", "plan", ["e2e", "lint", "review", "docs", "security"]))
    out.append(derived("fixes", "review", ["docs", "security"]))
    by_label = {st["label"]: st for st in out}
    return [by_label[lbl] for lbl in
            ("plan", "impl", "e2e", "lint", "review", "fixes", "docs", "security")]


def _parse_usage() -> dict | None:
    try:
        raw = json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return None
    cu = raw.get("cachedUsageUtilization") or {}
    limits = []
    for lim in (cu.get("utilization") or {}).get("limits") or []:
        if not isinstance(lim, dict):
            continue
        kind = str(lim.get("kind") or "?")
        label = LIMIT_LABELS.get(kind, kind)
        short = SHORT_LABELS.get(kind, kind)
        model = ((lim.get("scope") or {}).get("model") or {}).get("display_name")
        limits.append(
            {
                "label": f"{label} {model}" if model else label,
                "short": (f"{short} {model}" if model else short),
                "percent": lim.get("percent") or 0,
                "severity": lim.get("severity") or "normal",
                "resetsAt": lim.get("resets_at"),
                "active": bool(lim.get("is_active")),
            }
        )
    if not limits:
        return None
    tier = (raw.get("oauthAccount") or {}).get("userRateLimitTier") or ""
    return {
        "plan": tier.replace("default_", "").replace("claude_", "").replace("_", " "),
        "fetchedAt": (cu.get("fetchedAtMs") or 0) / 1000,
        "limits": limits,
    }


def read_usage() -> dict | None:
    """Plan utilization (what /usage shows). Claude Code caches it in ~/.claude.json;
    we never query the API ourselves, so the number is only as fresh as the cache -
    which is why fetchedAt travels with it."""
    try:
        mtime = os.stat(CONFIG).st_mtime
    except OSError:
        return None
    if _usage["mtime"] != mtime:
        _usage["mtime"] = mtime
        _usage["data"] = _parse_usage()
    return _usage["data"]


def code_version() -> str:
    """vYYYYMMDD-commit of the checkout this script runs from - the date is the
    commit's, not today's, so the same code always reports the same version. The
    plugin can be installed outside git, then only the file date is known."""
    here = Path(__file__).resolve()
    try:
        r = subprocess.run(
            ["git", "-C", str(here.parent), "log", "-1",
             "--format=v%cd-%h", "--date=format:%Y%m%d"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return time.strftime("v%Y%m%d", time.localtime(here.stat().st_mtime))


def git_branch(cwd: str, cache: dict[str, str | None]) -> str | None:
    """Live branch of the working directory. A branch belongs to the worktree, not
    the session - the one recorded in the transcript is stale for idle sessions."""
    if cwd in cache:
        return cache[cwd]
    b = None
    try:
        r = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            b = r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    cache[cwd] = b
    return b


# The .app that a process ultimately belongs to - "Cursor" out of
# /Applications/Cursor.app/Contents/MacOS/Cursor.
APP_RE = re.compile(r"/([^/]+)\.app/Contents/MacOS/")
MAX_ANCESTRY = 12


def proc_table() -> dict[int, tuple[int, str, str]]:
    """pid -> (ppid, tty, command) for every process; one ps call per tick."""
    try:
        r = subprocess.run(
            ["ps", "-Ao", "pid=,ppid=,tty=,command="],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    out: dict[int, tuple[int, str, str]] = {}
    for line in r.stdout.splitlines():
        f = line.split(None, 3)
        if len(f) < 4:
            continue
        try:
            out[int(f[0])] = (int(f[1]), f[2], f[3])
        except ValueError:
            continue
    return out


def host(pid: int | None, procs: dict) -> dict | None:
    """Which terminal window is this session sitting in? Walk the parent chain
    (claude -> zsh -> pty-host -> Cursor.app) until an .app turns up. Under tmux or
    over ssh nothing owns the session any more and there is nothing to focus."""
    if not pid:
        return None
    tty = (procs.get(pid) or (0, "", ""))[1]
    seen = 0
    while pid > 1 and seen < MAX_ANCESTRY:
        e = procs.get(pid)
        if not e:
            return None
        m = APP_RE.search(e[2])
        if m:
            return {"app": m.group(1), "tty": tty if tty not in ("??", "-") else ""}
        pid, seen = e[0], seen + 1
    return None


def _q(s: str) -> str:
    """AppleScript string literal."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# An editor keeps one window per open folder, so `open -a <editor> <cwd>` lands on
# the very window the session runs in - and unlike System Events it needs no
# Accessibility grant. A terminal emulator would just open a new window instead.
EDITORS = {"Cursor", "Code", "VSCodium", "Windsurf", "Zed", "Positron"}


def tab_script(app: str, dev: str) -> str | None:
    """Terminal and iTerm publish the tty of every tab, so the exact tab can be
    raised - the only two apps where focus is precise rather than approximate."""
    if app == "Terminal":
        return f'''tell application "Terminal"
  activate
  repeat with w in windows
    repeat with t in tabs of w
      if tty of t is {_q(dev)} then
        set selected of t to true
        set index of w to 1
        return "tab"
      end if
    end repeat
  end repeat
end tell
return "app"'''
    if app.startswith("iTerm"):
        return f'''tell application {_q(app)}
  activate
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        if tty of s is {_q(dev)} then
          select w
          select t
          select s
          return "tab"
        end if
      end repeat
    end repeat
  end repeat
end tell
return "app"'''
    return None


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    if r.returncode == 0:
        return True, r.stdout.strip()
    err = r.stderr.strip().splitlines()
    return False, err[-1] if err else "failed"


def focus(pid: int, cwd: str) -> dict:
    """Bring the terminal window this session runs in to the front."""
    h = host(pid, proc_table())
    if not h:
        return {"ok": False, "error": "no terminal app owns this session"}
    app = h["app"]
    script = tab_script(app, f"/dev/{h['tty']}") if h["tty"] else None
    if script:
        ok, out = _run(["osascript", "-e", script])
        scope = out or "app"
    elif app in EDITORS and cwd:
        ok, out = _run(["open", "-a", app, cwd])
        scope = "window"
    else:
        ok, out = _run(["osascript", "-e", f"tell application {_q(app)} to activate"])
        scope = "app"
    return {"ok": True, "app": app, "scope": scope} if ok else {"ok": False, "error": out}


def agents_json() -> list[dict]:
    try:
        raw = subprocess.run(
            ["claude", "agents", "--json"], capture_output=True, text=True, timeout=20
        )
        return json.loads(raw.stdout) if raw.returncode == 0 else []
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def build_state() -> dict:
    sessions = []
    branches: dict[str, str | None] = {}
    procs = proc_table()
    for s in agents_json():
        sid = s.get("sessionId", "")
        path = transcript(sid)
        t = scan(path) if path else _fresh()
        limit = CONTEXT_LIMITS.get(t["model"] or "", DEFAULT_LIMIT)
        try:
            mtime = os.stat(path).st_mtime if path else 0
        except OSError:
            mtime = 0
        subs = subagents(path, sid) if path else []
        # Busy with nothing delegated = the main context itself is working.
        main_busy = s.get("status") == "busy" and not any(a["active"] for a in subs)
        branch = git_branch(s.get("cwd", ""), branches) or t["branch"]
        att = attention(s, sid, mtime)
        if att:  # only a waiting session shows what it last said
            att["lastAgent"] = t["last_agent"]
        sessions.append(
            {
                "name": s.get("name") or sid[:8],
                "sessionId": sid,
                "pid": s.get("pid"),
                "kind": s.get("kind"),
                "status": s.get("status"),
                "attention": att,
                "cwd": s.get("cwd", ""),
                "project": os.path.basename(s.get("cwd", "")) or "?",
                "startedAt": s.get("startedAt"),
                "branch": branch,
                "model": t["model"],
                "effort": t["effort"],
                "turns": t["turns"],
                "context": t["context"],
                "contextLimit": limit,
                "tokens": {
                    k: t[k]
                    for k in ("input", "output", "cache_read", "cache_write", "thinking")
                },
                "mtime": mtime,
                "host": (host(s.get("pid"), procs) or {}).get("app"),
                "subagents": subs,
                "steps": feature_steps(subs, main_busy, t["feature_run"]),
                "mainBusy": main_busy,
            }
        )

    sessions.sort(key=lambda s: (not s["attention"], s["status"] != "busy", -s["mtime"]))
    totals = {
        "sessions": len(sessions),
        "waiting": sum(1 for s in sessions if s["attention"]),
        "busy": sum(1 for s in sessions if s["status"] == "busy"),
        "subagents": sum(len(s["subagents"]) for s in sessions),
        "output": sum(s["tokens"]["output"] for s in sessions),
        "input": sum(s["tokens"]["input"] for s in sessions),
        "cache_read": sum(s["tokens"]["cache_read"] for s in sessions),
        "cache_write": sum(s["tokens"]["cache_write"] for s in sessions),
        "thinking": sum(s["tokens"]["thinking"] for s in sessions),
        "turns": sum(s["turns"] for s in sessions),
        "context": sum(s["context"] for s in sessions),
    }
    return {
        "now": time.time(),
        "usage": read_usage(),
        "sessions": sessions,
        "totals": totals,
    }


PAGE = r"""<!doctype html>
<meta charset="utf-8"><title>Claude agents</title>
<style>
:root{--bg:#191817;--card:#232120;--fg:#f0eee9;--dim:#9a938a;--line:#35322f;
      --busy:#f0906a;--idle:#7cc292;--warn:#e0a94a;--bar:#d97757;--bar2:#3d3936;
      --att:#ffb02e}
*{box-sizing:border-box}
body{margin:0;padding:18px;background:var(--bg);color:var(--fg);
     font:14px/1.45 ui-sans-serif,-apple-system,system-ui,sans-serif}
h1{font-size:16px;margin:0 0 2px;font-weight:650}
.sub{color:var(--dim);font-size:12px;margin-bottom:16px}
.iv{background:none;border:1px solid var(--line);border-radius:5px;color:var(--dim);
    font:inherit;padding:0 6px;cursor:pointer;font-variant-numeric:tabular-nums}
.iv:hover{border-color:var(--dim);color:var(--fg)}
.kpis{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.kpi.plan{min-width:86px}
.kpi.plan.on{border-color:var(--busy)}
.kpi .bar{margin:6px 0 0}
.kpi.hot .bar>i{background:var(--warn)}
.kpi.max .bar>i{background:#f2776b}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px}
.kpis:not(.all) .kpi.more-only{display:none}
.more{background:none;border:1px dashed var(--line);border-radius:8px;color:var(--dim);
      padding:8px 12px;font:inherit;font-size:11px;text-transform:uppercase;
      letter-spacing:.04em;cursor:pointer;text-align:center}
.more i{display:block;font-size:19px;font-style:normal;line-height:1}
.more:hover{border-color:var(--dim);color:var(--fg)}
.kpi b{display:block;font-size:19px;font-variant-numeric:tabular-nums}
.kpi span{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.04em}
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(340px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card.idle{background:#1d1b1a;border-color:#2b2927;color:var(--dim)}
.card.idle .toks b,.card.idle h2{color:#c9c2b8}
.card.att{border:2px solid var(--att);padding:11px 13px;
          box-shadow:0 0 0 3px rgba(255,176,46,.16),0 0 30px -6px var(--att);
          animation:pulse 1.8s ease-in-out infinite}
@keyframes pulse{50%{box-shadow:0 0 0 3px rgba(255,176,46,.04),0 0 8px -4px var(--att)}}
@media (prefers-reduced-motion:reduce){
  .card.att,.st.running{animation:none}
  .spin{animation:none;border-top-color:currentColor}
}
.head{display:flex;align-items:baseline;gap:8px;margin-bottom:2px}
.head h2{font-size:14px;margin:0;font-weight:620;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.go{font-size:10px;padding:2px 7px;border-radius:99px;border:1px solid var(--line);
    background:none;color:var(--dim);font:inherit;font-size:10px;text-transform:uppercase;
    letter-spacing:.05em;font-weight:600;cursor:pointer;flex:none}
.go:hover{border-color:var(--busy);color:var(--busy)}
.go:disabled{opacity:.4;cursor:default}
.card.att .go{border-color:var(--att);color:var(--att)}
.pill{font-size:10px;padding:2px 7px;border-radius:99px;border:1px solid currentColor;
      text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.pill.busy{color:var(--busy)}.pill.idle{color:var(--idle)}
.spin{display:inline-block;vertical-align:-1px;width:8px;height:8px;margin-right:5px;
      border:1.5px solid currentColor;border-top-color:transparent;border-radius:99px;
      animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.pill.att{color:#191817;background:var(--att);border-color:var(--att)}
.att-row{background:#3a2c12;border:1px solid var(--att);border-radius:7px;
         padding:6px 9px;margin:0 0 9px;font-size:12.5px;line-height:1.4}
.att-row b{color:var(--att)}
.att-row .d{color:var(--dim);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.att-row .say{margin-top:4px;color:var(--dim);cursor:pointer;overflow:hidden;
              display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.att-row .say::before{content:"\25be ";color:var(--att)}
.att-row .say.open{display:block;white-space:pre-wrap}
.att-row .say.open::before{content:"\25b4 "}
.kpi.att b{color:var(--att)}
.branch{font-size:12px;font-weight:560;color:var(--fg);opacity:.75;margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.meta{color:var(--dim);font-size:12px;margin-bottom:9px}
.bar{height:5px;background:var(--bar2);border-radius:99px;overflow:hidden;margin:3px 0 5px}
.bar>i{display:block;height:100%;background:var(--bar)}
.toks{display:grid;grid-template-columns:1fr 1fr;gap:1px 12px;font-size:12px;color:var(--dim)}
.toks b{color:var(--fg);font-weight:550;font-variant-numeric:tabular-nums;float:right}
.subs{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}
.subs>div{display:flex;gap:7px;align-items:baseline;font-size:12px;padding:2px 0}
.dot{width:6px;height:6px;border-radius:99px;background:var(--bar2);flex:none;margin-top:5px}
.dot.on{background:var(--busy)}
.sa-name{font-weight:550;white-space:nowrap}
.sa-desc{color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.sa-tok{color:var(--dim);font-variant-numeric:tabular-nums;flex:none}
.steps{margin-top:10px;border-top:1px solid var(--line);padding-top:8px;
       display:flex;gap:4px;flex-wrap:wrap}
.st{font-style:normal;font-size:11px;padding:1px 6px;border-radius:5px;
    border:1px solid var(--line);color:var(--dim)}
.st.done{border-color:var(--idle);color:var(--idle)}
.st.running{border-color:var(--att);color:var(--att);animation:blink 1.6s ease-in-out infinite}
.st.unrun{border-style:dashed;opacity:.35}
.st.main{margin-right:4px}
.st.main.unrun{opacity:.25}
@keyframes blink{50%{opacity:.4}}
.ver{position:absolute;top:18px;right:18px;color:var(--dim);font-size:11px;
     font-variant-numeric:tabular-nums}
</style>
<div class="ver">__VERSION__</div>
<h1>Claude agents dashboard</h1>
<div class="sub" id="sub">loading…</div>
<div class="kpis" id="kpis"></div>
<div class="grid" id="grid"></div>
<script>
const n = v => v >= 1e6 ? (v/1e6).toFixed(2)+"M" : v >= 1e3 ? Math.round(v/1e3)+"k" : String(v||0);
const dur = s => s < 60 ? Math.round(s)+" s" : s < 3600 ? Math.round(s/60)+" min"
  : s < 86400 ? (s/3600).toFixed(1)+" h" : (s/86400).toFixed(1)+" d";
const ago = (t, now) => dur(Math.max(0, now - t));
const esc = s => (s||"").replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));

function kpi(v, l, c){ return `<div class="kpi ${c||""}"><b>${v}</b><span>${l}</span></div>`; }

// click the interval in the sub line to cycle it; like the KPI fold, the state has to
// live outside the DOM because the sub line is rewritten on every tick
const INTERVALS = [[3000, "3 s"], [10000, "10 s"], [60000, "1 min"], [0, "stop"]];
let ivIdx = 0, timer = null;
function arm(){
  clearInterval(timer);
  const ms = INTERVALS[ivIdx][0];
  if(ms) timer = setInterval(tick, ms);  // "stop" is 0 - no timer, not a very long one
}
function cycleRefresh(){
  ivIdx = (ivIdx + 1) % INTERVALS.length;
  arm();
  // tick() repaints the label too, but only once its fetch resolves - a click has to
  // answer immediately, so write it here as well
  document.querySelector(".iv").textContent = INTERVALS[ivIdx][1];
  tick();
}

// the KPI row is rebuilt every tick, so the fold state lives out here, not in the DOM
let kpisAll = false;
function toggleKpis(){
  kpisAll = !kpisAll;
  paintKpiFold();
}
function paintKpiFold(){
  const el = document.getElementById("kpis");
  el.classList.toggle("all", kpisAll);
  const b = el.querySelector(".more");
  if(b){
    b.querySelector("i").textContent = kpisAll ? "\u2190" : "\u2192";
    b.querySelector("span").textContent = kpisAll ? "show less" : "show more";
  }
}

// share of the input side served from the cache - what keeps a long session cheap
function hit(T){
  const all = T.cache_read + T.cache_write + T.input;
  return all ? Math.round(100 * T.cache_read / all) + "%" : "–";
}

// plan utilization as a KPI tile - the long label and the countdown are in the tooltip
function planKpis(u, now){
  if(!u) return "";
  return u.limits.map(l => {
    const p = Math.max(0, Math.min(100, l.percent));
    const cls = (p >= 90 || l.severity === "critical") ? "max"
              : (p >= 70 || l.severity === "warning") ? "hot" : "";
    const reset = l.resetsAt
      ? " · resets in " + dur(Math.max(0, Date.parse(l.resetsAt)/1000 - now)) : "";
    const age = " · from the Claude Code cache, " + ago(u.fetchedAt, now) + " old";
    return `<div class="kpi plan ${cls}${l.active ? " on" : ""}"`
      + ` title="${esc(l.label)}${reset}${age}">`
      + `<b>${Math.round(p)} %</b><span>${esc(l.short)}</span>`
      + `<div class="bar"><i style="width:${p}%"></i></div></div>`;
  }).join("");
}

// The checking steps of /feature:start, straight out of the subagent tree: green ran,
// orange is running, dashed never ran. `review x2` is a second round of the same step.
function steps(s, now){
  if(!s.steps) return "";
  const main = `<i class="st main ${s.mainBusy ? "running" : "unrun"}" title="${
    s.mainBusy ? "the main context is working - nothing is delegated right now"
               : "the main context is not working"}">main</i>`;
  return `<div class="steps">` + main + s.steps.map(t => `<i class="st ${t.state}" title="${
    esc(t.mtime ? `${t.verdict ? t.verdict + " \u00b7 " : ""}${t.attempts} run${
      t.attempts > 1 ? "s" : ""}, last ${ago(t.mtime, now)} ago`
      : t.state === "unrun" ? "has not run"
      : "runs in the main context - read off the order of the workflow")}">${
    esc(t.label)}${t.flag ? "*" : ""}${
    t.attempts > 1 ? " &times;" + t.attempts : ""}</i>`).join("") + `</div>`;
}

// same reason as the KPI fold: the cards are rebuilt every tick
const expanded = new Set();  // sessions whose last agent message is unfolded
document.getElementById("grid").addEventListener("click", ev => {
  const go = ev.target.closest(".go");
  if(go){ focusSession(go); return; }
  const el = ev.target.closest(".say");
  if(!el) return;
  const sid = el.dataset.sid;
  expanded.has(sid) ? expanded.delete(sid) : expanded.add(sid);
  el.classList.toggle("open");
});

// The page has no way to raise a native window, so the server does it over
// AppleScript; the button reports back in place because the window that comes
// forward is not this one - the user is looking elsewhere by then.
async function focusSession(btn){
  const label = btn.innerHTML;
  btn.disabled = true;
  try {
    const r = await (await fetch("/api/focus", {method: "POST", headers: {
      "Content-Type": "application/json"}, body: JSON.stringify({
        pid: Number(btn.dataset.pid), cwd: btn.dataset.cwd})})).json();
    if(!r.ok) throw new Error(r.error || "failed");
  } catch (e) {
    btn.innerHTML = "\u2717 " + esc(String(e.message || e)).slice(0, 40);
    btn.title = String(e.message || e);
    setTimeout(() => { btn.innerHTML = label; btn.disabled = false; }, 4000);
    return;
  }
  btn.disabled = false;
}

function card(s, now){
  const a = s.attention;
  const st = a ? "att" : s.status;
  const pct = s.contextLimit ? Math.min(100, 100*s.context/s.contextLimit) : 0;
  const t = s.tokens;
  const subs = s.subagents.map(a => `<div>
      <i class="dot ${a.active?"on":""}"></i>
      <span class="sa-name">${esc(a.type)}</span>
      <span class="sa-desc">${esc(a.desc)}</span>
      <span class="sa-tok">${n(a.tokens.output)} out · ${ago(a.mtime, now)}</span></div>`).join("");
  const said = a && a.lastAgent;
  const att = a ? `<div class="att-row">&#9203; <b>${esc(a.label)}</b> &middot; ${ago(a.since, now)}
      ${a.detail ? `<span class="d">${esc(a.detail)}</span>` : ""}
      ${said ? `<div class="say${expanded.has(s.sessionId) ? " open" : ""}"
        data-sid="${esc(s.sessionId)}" title="click to expand">${esc(said.text)}</div>` : ""
      }</div>` : "";
  return `<div class="card ${st}">
    <div class="head"><h2>${esc(s.project)}</h2>
      ${s.host ? `<button class="go" data-pid="${s.pid}" data-cwd="${esc(s.cwd)}"
        title="bring the ${esc(s.host)} window running this session to the front"
        >&#8599; ${esc(s.host)}</button>` : ""}
      <span class="pill ${st}">${st === "busy" ? '<i class="spin"></i>' : ""}${
        a ? "needs you" : st}</span></div>
    ${s.branch ? `<div class="branch">${esc(s.branch)}</div>` : ""}
    <div class="meta">${esc(s.kind)}
      · pid ${s.pid} · ${esc(s.name)} · ${esc(s.model||"?")}${s.effort?" / "+esc(s.effort):""}
      <br>${s.turns} turns · active ${ago(s.mtime, now)} ago</div>
    ${att}
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="toks">
      <div>context <b>${n(s.context)} / ${n(s.contextLimit)}</b></div>
      <div>output <b>${n(t.output)}</b></div>
      <div>cache read <b>${n(t.cache_read)}</b></div>
      <div>cache write <b>${n(t.cache_write)}</b></div>
      <div>input <b>${n(t.input)}</b></div>
      <div>thinking <b>${n(t.thinking)}</b></div>
    </div>
    ${steps(s, now)}
    ${subs ? `<div class="subs">${subs}</div>` : ""}
  </div>`;
}

async function tick(){
  try {
    const d = await (await fetch("/api/state")).json();
    const T = d.totals, now = d.now;
    const U = d.usage;
    document.getElementById("sub").innerHTML =
      "updated " + new Date().toLocaleTimeString() + " · auto-refresh "
      + `<button class="iv" onclick="cycleRefresh()" title="click to change the interval">`
      + INTERVALS[ivIdx][1] + `</button>`;
    document.getElementById("kpis").innerHTML =
      planKpis(U, now)
      + kpi(T.sessions, "sessions") + kpi(T.busy, "busy")
      + `<div class="kpi${T.waiting ? " att" : ""}"><b>${T.waiting}</b>`
      + `<span>need you</span></div>`
      + kpi(n(T.context), "context total")
      + kpi(n(T.output), "output tokens") + kpi(hit(T), "cache hit")
      + kpi(T.subagents, "subagents", "more-only")
      + kpi(T.turns, "turns", "more-only")
      + kpi(n(T.input), "input tokens", "more-only")
      + kpi(n(T.thinking), "thinking", "more-only")
      + kpi(n(T.cache_read), "cache read", "more-only")
      + kpi(n(T.cache_write), "cache write", "more-only")
      + (U ? kpi(esc(U.plan), "plan", "more-only") : "")
      + `<button class="more" onclick="toggleKpis()"><i>\u2192</i><span>show more</span></button>`;
    paintKpiFold();
    document.getElementById("grid").innerHTML = d.sessions.map(s => card(s, now)).join("");
    document.title = (T.waiting ? `(${T.waiting}) ` : "") + "Claude agents";
  } catch (e) {
    document.getElementById("sub").textContent = "connection to the server failed: " + e;
  }
}
tick(); arm();
</script>
"""
PAGE = PAGE.replace("__VERSION__", code_version())


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/state"):
            with _lock:
                body = json.dumps(build_state()).encode()
            ctype = "application/json"
        elif self.path in ("/", "/index.html"):
            body, ctype = PAGE.encode(), "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/api/focus"):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
            res = focus(int(req["pid"]), str(req.get("cwd") or ""))
        except (ValueError, KeyError, TypeError) as e:
            res = {"ok": False, "error": str(e)}
        body = json.dumps(res).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # quiet
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Live dashboard of Claude Code sessions")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--open", action="store_true", help="open a browser window")
    args = ap.parse_args()

    url = f"http://127.0.0.1:{args.port}/"
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Claude monitor: {url}  (Ctrl-C to quit)")
    if args.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
