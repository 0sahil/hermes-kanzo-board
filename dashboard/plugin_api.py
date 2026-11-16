"""Kanzo backend: thin proxy to the local Kanzo board's HTTP API.

GET  /board?project=&q=&done=   -> Kanzo /api/board
GET  /task/{id}                 -> Kanzo /api/tasks/{id}
POST /move {id,status,before}   -> Kanzo /api/tasks/{id}/move
Board URL: $KANZO_URL, else http://127.0.0.1:<port from $KANZO_HOME|~/kanzo/config.toml>.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


def _base() -> str:
    if os.environ.get("KANZO_URL"):
        return os.environ["KANZO_URL"].rstrip("/")
    home = Path(os.environ.get("KANZO_HOME") or Path.home() / "kanzo")
    port = 4242
    try:
        m = re.search(r"^\s*port\s*=\s*(\d+)", (home / "config.toml").read_text(), re.M)
        if m:
            port = int(m.group(1))
    except OSError:
        pass
    return f"http://127.0.0.1:{port}"


def _call(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        _base() + "/api" + path, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("error", e.reason)
        except Exception:
            msg = e.reason
        raise HTTPException(e.code, msg)
    except Exception as e:
        raise HTTPException(502, f"Kanzo board not reachable at {_base()}: {e}")


@router.get("/board")
def board(project: str = "", q: str = "", done: str = ""):
    qs = urllib.parse.urlencode({k: v for k, v in
                                 {"project": project, "q": q, "done": done}.items() if v} or {"project": ""})
    data = _call("GET", "/board?" + qs)
    data["url"] = _base()
    return data


@router.get("/task/{task_id}")
def task(task_id: int):
    return _call("GET", f"/tasks/{task_id}")


class Move(BaseModel):
    id: int
    status: str
    before: Optional[int] = None


@router.post("/move")
def move(m: Move):
    return _call("POST", f"/tasks/{m.id}/move", {"status": m.status, "before": m.before})
