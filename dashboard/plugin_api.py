"""Kanzo for Hermes Desktop: backend for the embedded board.

The desktop page runs the user's own Kanzo web UI (fetched from their running
board, never bundled) inside a sandboxed frame. The frame cannot reach the board
itself, so every request it makes comes through here:

    POST /shell   -> {"html", "base", "version"}: the board's UI as one frame document
                     (see frame.py); body {"storage": {...}} seeds its localStorage
    POST /proxy   -> one request to the board, {"method","path","body","b64","ctype"}
                     answered as {"status","ctype","version","body","b64"}

Board URL: $KANZO_URL, else http://127.0.0.1:<port from $KANZO_HOME/config.toml or ~/kanzo>.
"""
from __future__ import annotations

import base64
import importlib.util
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_TEXT = re.compile(r"^(text/|application/(json|javascript|xml|manifest\+json))")


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


def _request(method: str, path: str, data: Optional[bytes] = None, ctype: Optional[str] = None):
    if not path.startswith("/") or path.startswith("//"):
        raise HTTPException(400, "path must be board-relative")
    headers = {"Content-Type": ctype} if (data is not None and ctype) else {}
    req = urllib.request.Request(_base() + path, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()
    except Exception as e:
        raise HTTPException(502, f"Kanzo board not reachable at {_base()}: {e}")


def _frame():
    """The sibling frame.py, loaded by path (the host imports this file with no package).
    Loaded per request so a plugin update/reload never serves a stale copy; it is tiny."""
    spec = importlib.util.spec_from_file_location("hermes_plugin_kanzo_frame", Path(__file__).with_name("frame.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ShellReq(BaseModel):
    storage: Optional[dict] = None


@router.post("/shell")
def shell(r: ShellReq):
    s1, h1, index = _request("GET", "/")
    s2, _, app = _request("GET", "/app.js")
    if s1 != 200 or s2 != 200:
        raise HTTPException(502, f"Kanzo board at {_base()} answered {s1}/{s2}")
    base = _base() + "/"
    html = _frame().build(index.decode("utf-8"), app.decode("utf-8"), base, r.storage or {})
    return {"html": html, "base": base, "version": h1.get("x-kanzo-version")}


class ProxyReq(BaseModel):
    method: str = "GET"
    path: str
    body: Optional[str] = None
    b64: bool = False
    ctype: Optional[str] = None


@router.post("/proxy")
def proxy(r: ProxyReq):
    data = None
    if r.body is not None:
        data = base64.b64decode(r.body) if r.b64 else r.body.encode("utf-8")
    status, headers, raw = _request(r.method, r.path, data, r.ctype)
    ctype = headers.get("content-type", "") if headers else ""
    out = {"status": status, "ctype": ctype, "version": headers.get("x-kanzo-version") if headers else None}
    if not raw or _TEXT.match(ctype or ""):
        out.update(body=raw.decode("utf-8", "replace"), b64=False)
    else:
        out.update(body=base64.b64encode(raw).decode("ascii"), b64=True)
    return out
