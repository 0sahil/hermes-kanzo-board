"""Builds the frame document: the user's own Kanzo index.html + app.js, adapted
to run inside Hermes Desktop's sandboxed (opaque-origin) frame.

Nothing of Kanzo is bundled with this plugin; both files come from the running
board at request time and are only rewritten in memory.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CONFIRM = re.compile(r"(?<![\w.$])confirm\(")
_ARROW = re.compile(r"(\((?:[^()]|\([^()]*\))*\)|[\w$]+)\s*=>\s*\Z")
_FUNC = re.compile(r"\bfunction\b\s*\*?\s*[\w$]*\s*\((?:[^()]|\([^()]*\))*\)\s*\Z")
_METHOD = re.compile(r"(?:^|[\s,{;])([\w$]+)\s*\((?:[^()]|\([^()]*\))*\)\s*\Z")
_KEYWORDS = {"if", "for", "while", "switch", "catch", "with", "function"}
_ASYNC_BEFORE = re.compile(r"async\s*\Z")


def make_async_confirm(src: str) -> str:
    """Turn every confirm(...) into `await __kzConfirm(...)` and mark the enclosing
    function async. The sandbox has no native modals; the frame shows its own dialog.
    The result is compile-checked in the frame, with `sync_confirm` as the fallback."""
    inserts: set[int] = set()
    for m in CONFIRM.finditer(src):
        depth = 0
        for i in range(m.start() - 1, -1, -1):
            c = src[i]
            if c == "}":
                depth += 1
                continue
            if c != "{":
                continue
            if depth:
                depth -= 1
                continue
            start = max(0, i - 300)
            head = src[start:i]
            pos = -1
            if (mm := _ARROW.search(head)):
                pos = start + mm.start()
            elif (mm := _FUNC.search(head)):
                pos = start + mm.start()
            elif (mm := _METHOD.search(head)) and mm.group(1) not in _KEYWORDS:
                pos = start + mm.start(1)
            else:
                continue  # plain block (if/else/try/loop): keep walking outward
            if not _ASYNC_BEFORE.search(src[max(0, pos - 10):pos]):
                inserts.add(pos)
            break
    out = src
    for pos in sorted(inserts, reverse=True):
        out = out[:pos] + "async " + out[pos:]
    return CONFIRM.sub("await __kzConfirm(", out)


def sync_confirm(src: str) -> str:
    """Fallback: confirm() always answers Cancel, never a silent destructive yes."""
    return CONFIRM.sub("__kzConfirmSync(", src)


def adapt(src: str) -> str:
    src = re.sub(r"(?<![\w.$])localStorage(?![\w$])", "__kzStorage", src)
    return re.sub(r"\blocation\.hostname\b", "__KZ_HOST", src)


def _script_json(value) -> str:
    return json.dumps(value).replace("</", "<\\/").replace("<!--", "<\\!--")


def build(index: str, app: str, base: str, storage: dict) -> str:
    adapted = adapt(app)
    cfg = {
        "base": base,
        "storage": storage or {},
        "asyncSource": make_async_confirm(adapted),
        "syncSource": sync_confirm(adapted),
    }
    bridge = (Path(__file__).with_name("bridge.js")).read_text("utf-8")
    base_attr = base.replace("&", "&amp;").replace('"', "&quot;")
    head = (f'<base href="{base_attr}">'
            f"<script>window.__KZ_CFG={_script_json(cfg)};</script>"
            f"<script>{bridge}</script>")
    html, n = re.subn(r"<head[^>]*>", lambda m: m.group(0) + head, index, count=1, flags=re.I)
    if not n:
        html = head + index
    run = "<script>__kzRun()</script>"
    html, n = re.subn(r"""<script\b[^>]*\bsrc=["']/?app\.js["'][^>]*>\s*</script>""", run, html, count=1, flags=re.I)
    if not n:
        html = re.sub(r"</body>", run + "</body>", html, count=1, flags=re.I) if re.search(r"</body>", html, re.I) else html + run
    return html
