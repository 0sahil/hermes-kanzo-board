"""Kanzo Board: backend routes, mounted by Hermes at /api/plugins/kanzo-board/.

Board (the page shows the board's own web UI in a sandboxed frame; see frame.py):
    POST /shell    {"storage": {...}}  -> {"html", "base", "version"}
    POST /proxy    one request from the frame to the board -> {"status","ctype","version","body","b64"}

Setup (each runs only when the user clicks the matching button on the page):
    GET  /status                       -> board, Kanzo program, release and agent-tools state
    POST /setup/install                -> install the pinned official Kanzo release
    POST /setup/start  {"mode"}        -> "service" (kanzo service install) or "now" (kanzo --no-open)
    POST /setup/join   {"host"}        -> kanzo join <host>
    POST /setup/mcp                    -> hermes mcp add <kanzo's MCP server>
"""
from __future__ import annotations

import base64
import importlib.util
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
_HERE = Path(__file__).parent
_TEXT = re.compile(r"^(text/|application/(json|javascript|xml|manifest\+json))")


def _sibling(name: str):
    """A sibling module, loaded by path: Hermes imports this file without a package."""
    spec = importlib.util.spec_from_file_location(f"hermes_plugin_kanzo_board_{name}", _HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _sibling("kanzo_core")


def _fail(e: Exception):
    if isinstance(e, core.SetupError):
        raise HTTPException(400, str(e))
    raise HTTPException(500, f"{type(e).__name__}: {e}")


def _data_dir() -> Path:
    """`plugin-data/kanzo-board` in the active profile's Hermes home."""
    try:
        from hermes_constants import get_hermes_home
        home = Path(get_hermes_home())
    except Exception:
        home = Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")
    return home / "plugin-data" / core.PLUGIN_ID


def _status() -> dict:
    url, source = core.board_url()
    exe = core.find_kanzo()
    rel = core.release()
    tgt = core.target()
    return {
        "board": {"url": url, "source": source, **core.board_status(url)},
        "kanzo": {"path": str(exe), "version": core.kanzo_version(exe)} if exe else None,
        "release": {"version": rel["version"], "repository": rel["repository"],
                    "supported": bool(tgt and tgt in rel["assets"]),
                    "install_dir": str(core.install_dir())},
        "mcp": {"server": core.mcp_server()},
    }


# --- board ----------------------------------------------------------------------------------------


class ShellReq(BaseModel):
    storage: Optional[dict] = None


@router.post("/shell")
def shell(r: ShellReq):
    url, _ = core.board_url()
    try:
        s1, h1, index = core.board_request(url, "GET", "/")
        s2, _, app = core.board_request(url, "GET", "/app.js")
    except core.SetupError as e:
        raise HTTPException(502, str(e))
    if s1 != 200 or s2 != 200 or not h1.get("x-kanzo-version"):
        raise HTTPException(502, f"{url} did not answer like a Kanzo board ({s1}/{s2}).")
    html = _sibling("frame").build(index.decode("utf-8"), app.decode("utf-8"), url + "/", r.storage or {})
    return {"html": html, "base": url + "/", "version": h1.get("x-kanzo-version")}


class ProxyReq(BaseModel):
    method: str = "GET"
    path: str
    body: Optional[str] = None
    b64: bool = False
    ctype: Optional[str] = None


@router.post("/proxy")
def proxy(r: ProxyReq):
    url, _ = core.board_url()
    data = None
    if r.body is not None:
        data = base64.b64decode(r.body) if r.b64 else r.body.encode("utf-8")
    try:
        status, headers, raw = core.board_request(url, r.method, r.path, data, r.ctype)
    except core.SetupError as e:
        raise HTTPException(502, str(e))
    ctype = headers.get("content-type", "") if headers else ""
    out = {"status": status, "ctype": ctype, "version": headers.get("x-kanzo-version") if headers else None}
    if not raw or _TEXT.match(ctype or ""):
        out.update(body=raw.decode("utf-8", "replace"), b64=False)
    else:
        out.update(body=base64.b64encode(raw).decode("ascii"), b64=True)
    return out


# --- setup ----------------------------------------------------------------------------------------


@router.get("/status")
def status():
    try:
        return _status()
    except Exception as e:
        _fail(e)


@router.post("/setup/install")
def setup_install():
    try:
        if core.find_kanzo() is None:
            core.install_kanzo()
        return _status()
    except Exception as e:
        _fail(e)


class StartReq(BaseModel):
    mode: str = "service"


@router.post("/setup/start")
def setup_start(r: StartReq):
    try:
        exe = core.find_kanzo()
        if exe is None:
            raise core.SetupError("Kanzo is not installed on this computer.")
        url, source = core.board_url()
        if source != "local":
            raise core.SetupError("A board URL is set in the plugin settings; clear it to use this computer's board.")
        if r.mode == "now":
            core.start_now(exe, _data_dir())
        elif r.mode == "service":
            core.start_service(exe)
        else:
            raise core.SetupError("Unknown start mode.")
        if not core.wait_for_board(url):
            raise core.SetupError(f"Kanzo started but its board did not answer at {url} yet. Try again in a moment.")
        return _status()
    except Exception as e:
        _fail(e)


class JoinReq(BaseModel):
    host: str


@router.post("/setup/join")
def setup_join(r: JoinReq):
    try:
        exe = core.find_kanzo()
        if exe is None:
            raise core.SetupError("Joining a shared board needs Kanzo on this computer; install it first.")
        url, _ = core.board_url()
        if not core.board_status(url)["reachable"]:
            raise core.SetupError("Start this computer's board first; it shows the shared one once joined.")
        core.join(exe, r.host)
        return _status()
    except Exception as e:
        _fail(e)


@router.post("/setup/mcp")
def setup_mcp():
    try:
        url, source = core.board_url()
        if source == "setting":  # a board elsewhere: its MCP endpoint over HTTP (Kanzo's mcp_http)
            core.add_mcp(None, url)
        else:  # this computer's board: Kanzo's stdio server, as Kanzo's README sets it up
            core.add_mcp(core.find_kanzo(), None)
        return _status()
    except Exception as e:
        _fail(e)
