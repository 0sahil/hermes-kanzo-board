"""Everything the plugin does to Kanzo, outside the web framework (so it can be tested alone).

- find the board: the `board_url` plugin setting, else this computer's Kanzo port;
- talk to it (one request, path-checked);
- find, install and start Kanzo on this computer (the official release, pinned by SHA-256);
- join a board another computer shares (`kanzo join`);
- give the Hermes agent Kanzo's MCP tools (`hermes mcp add`).

Nothing here runs unless the user asks for it from the Kanzo Board page.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Mapping, Optional

PLUGIN_ID = "kanzo-board"
DEFAULT_PORT = 4242
RELEASE_FILE = Path(__file__).with_name("kanzo_release.json")
EXE = "kanzo.exe" if os.name == "nt" else "kanzo"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_HOST_RE = re.compile(r"^(?:\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9](?:[A-Za-z0-9.-]{0,253}[A-Za-z0-9])?)(?::\d{1,5})?$")


class SetupError(Exception):
    """A setup step failed; the message is shown to the user as is."""


# --- settings and the board's address ---------------------------------------------------------


def plugin_settings() -> dict[str, Any]:
    """`plugins.entries.kanzo-board.settings` from Hermes' config (read-only), or {}."""
    try:
        from hermes_cli.config import load_config_readonly  # documented for plugin backends
    except Exception:
        return {}
    try:
        entries = (load_config_readonly().get("plugins") or {}).get("entries") or {}
        settings = (entries.get(PLUGIN_ID) or {}).get("settings") or {}
        return dict(settings) if isinstance(settings, dict) else {}
    except Exception:
        return {}


def kanzo_home() -> Path:
    """Kanzo's data folder, as Kanzo itself resolves it: $KANZO_HOME, else ~/kanzo."""
    return Path(os.environ.get("KANZO_HOME") or Path.home() / "kanzo")


def local_port(home: Optional[Path] = None) -> int:
    try:
        text = ((home or kanzo_home()) / "config.toml").read_text("utf-8")
    except OSError:
        return DEFAULT_PORT
    m = re.search(r"^\s*port\s*=\s*(\d{1,5})\s*(?:#.*)?$", text, re.M)
    return int(m.group(1)) if m else DEFAULT_PORT


def normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not re.match(r"^https?://[^/\s?#@]+$", url):
        raise SetupError("The board URL must look like http://192.168.1.20:4242 (no path).")
    return url


def board_url(settings: Optional[dict] = None) -> tuple[str, str]:
    """(url, source): source is "setting" for a configured board, "local" for this computer's."""
    configured = (settings if settings is not None else plugin_settings()).get("board_url") or ""
    if str(configured).strip():
        return normalize_url(str(configured)), "setting"
    return f"http://127.0.0.1:{local_port()}", "local"


# --- talking to the board -----------------------------------------------------------------------


def board_request(base: str, method: str, path: str, data: Optional[bytes] = None,
                  ctype: Optional[str] = None, timeout: float = 30):
    """One request to the board. Returns (status, headers, body); raises SetupError if unreachable."""
    if not path.startswith("/") or path.startswith("//") or "\\" in path or any(c in path for c in "\r\n"):
        raise SetupError("Only paths on the board can be requested.")
    headers = {"Content-Type": ctype} if (data is not None and ctype) else {}
    req = urllib.request.Request(base + path, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()
    except Exception as e:
        raise SetupError(f"The Kanzo board at {base} is not reachable ({e}).")


def board_status(base: str) -> dict[str, Any]:
    """Whether a Kanzo board answers at `base` (every Kanzo reply carries x-kanzo-version)."""
    try:
        _, headers, _ = board_request(base, "GET", "/api/changes", timeout=3)
    except SetupError:
        return {"reachable": False, "version": None}
    version = headers.get("x-kanzo-version") if headers else None
    return {"reachable": bool(version), "version": version}


# --- Kanzo on this computer ---------------------------------------------------------------------


def release() -> dict[str, Any]:
    return json.loads(RELEASE_FILE.read_text("utf-8"))


def target(system: Optional[str] = None, machine: Optional[str] = None) -> Optional[str]:
    """The release target for this computer, or None when Kanzo publishes no build for it."""
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    arm64, x64 = machine in ("arm64", "aarch64"), machine in ("x86_64", "amd64")
    if system == "darwin":
        return "aarch64-apple-darwin" if arm64 else "x86_64-apple-darwin" if x64 else None
    if system == "linux":
        if x64:
            return "x86_64-unknown-linux-musl"
        if arm64:
            return "aarch64-unknown-linux-musl"
        if machine.startswith("armv7"):
            return "armv7-unknown-linux-musleabihf"
        if machine.startswith("armv6") or machine == "arm":
            return "arm-unknown-linux-musleabihf"
        return None
    if system == "windows":
        return "x86_64-pc-windows-msvc" if x64 else None
    return None


def install_dir() -> Path:
    """Where Kanzo's own installer puts it: $CARGO_HOME/bin, else ~/.cargo/bin."""
    cargo = os.environ.get("CARGO_HOME")
    return (Path(cargo) if cargo else Path.home() / ".cargo") / "bin"


def find_kanzo() -> Optional[Path]:
    """The kanzo program: on PATH, else the places Kanzo's installers use."""
    found = shutil.which("kanzo")
    if found:
        return Path(found)
    candidates = [install_dir() / EXE, Path.home() / ".local/bin" / EXE]
    if os.name != "nt":
        candidates += [Path("/opt/homebrew/bin/kanzo"), Path("/usr/local/bin/kanzo")]
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


# What a `kanzo` process gets from Hermes' environment: enough to find its folders, run its service
# manager (launchctl, systemctl --user, schtasks) and git over ssh, and nothing else, so Hermes'
# provider keys never reach it. Compared upper-cased (Windows names are case-insensitive).
_ENV_KEEP = frozenset({
    "PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "TEMP", "TMP", "TZ", "LANG", "LANGUAGE",
    "CARGO_HOME", "DBUS_SESSION_BUS_ADDRESS", "SSH_AUTH_SOCK", "DISPLAY", "WAYLAND_DISPLAY",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    # Windows
    "USERPROFILE", "USERNAME", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
    "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATHEXT",
})
_ENV_KEEP_PREFIXES = ("KANZO_", "XDG_", "LC_")


def kanzo_env(environ: Optional[Mapping[str, str]] = None) -> dict[str, str]:
    """The environment for a `kanzo` process: Hermes' own, filtered to `_ENV_KEEP`."""
    source: Mapping[str, str] = os.environ if environ is None else environ
    return {k: v for k, v in source.items()
            if k.upper() in _ENV_KEEP or k.upper().startswith(_ENV_KEEP_PREFIXES)}


def kanzo_version(exe: Path) -> Optional[str]:
    try:
        out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=10,
                             env=kanzo_env())
    except Exception:
        return None
    m = re.search(r"(\d+\.\d+\.\d+\S*)", out.stdout or "")
    return m.group(1) if m else None


def _download(url: str, limit: int = 64 << 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-kanzo-board"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read(limit + 1)
    except Exception as e:
        raise SetupError(f"Could not download {url} ({e}).")
    if len(data) > limit:
        raise SetupError("The download is larger than expected; stopped.")
    return data


def _program_from_archive(name: str, data: bytes) -> bytes:
    """The kanzo program inside a release archive, read without extracting anything to disk."""
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            members = [m for m in z.namelist() if m.rsplit("/", 1)[-1] == EXE]
            if len(members) != 1:
                raise SetupError("The release archive does not contain one kanzo program.")
            return z.read(members[0])
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
        members = [m for m in t.getmembers() if m.isfile() and m.name.rsplit("/", 1)[-1] == EXE]
        if len(members) != 1:
            raise SetupError("The release archive does not contain one kanzo program.")
        f = t.extractfile(members[0])
        if f is None:
            raise SetupError("The release archive could not be read.")
        return f.read()


def install_kanzo(dest_dir: Optional[Path] = None, fetch=_download) -> Path:
    """Install the pinned official Kanzo release. Refuses to replace an existing program."""
    rel = release()
    tgt = target()
    if tgt is None or tgt not in rel["assets"]:
        raise SetupError(f"Kanzo has no release for this computer ({platform.system()} {platform.machine()}). "
                         f"See {rel['repository']} to build it.")
    asset = rel["assets"][tgt]
    data = fetch(rel["download_base"] + asset["file"])
    digest = hashlib.sha256(data).hexdigest()
    if digest != asset["sha256"]:
        raise SetupError(f"The download did not match the pinned checksum (got {digest}); nothing was installed.")
    program = _program_from_archive(asset["file"], data)
    dest_dir = dest_dir or install_dir()
    dest = dest_dir / EXE
    if dest.exists():
        raise SetupError(f"{dest} already exists; not replacing it.")
    dest_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".kanzo-", dir=dest_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(program)
        os.chmod(tmp, os.stat(tmp).st_mode | stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return dest


def _run(args: list[str], timeout: float = 60, stdin: Optional[str] = None, hermes: bool = False) -> str:
    """Run a program to completion. `kanzo` gets `kanzo_env()`; only Hermes itself (`hermes=True`)
    inherits the full environment."""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=stdin,
                             env=None if hermes else kanzo_env())
    except subprocess.TimeoutExpired:
        raise SetupError(f"`{' '.join(Path(args[0]).name if i == 0 else a for i, a in enumerate(args))}` took too long.")
    except OSError as e:
        raise SetupError(f"Could not run {args[0]} ({e}).")
    if out.returncode != 0:
        msg = (out.stderr or out.stdout or "").strip().splitlines()
        raise SetupError(msg[-1] if msg else f"{Path(args[0]).name} exited with {out.returncode}.")
    return out.stdout


def wait_for_board(base: str, seconds: float = 15) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if board_status(base)["reachable"]:
            return True
        time.sleep(0.5)
    return False


def start_service(exe: Path) -> None:
    """`kanzo service install`: Kanzo's own login service (LaunchAgent, systemd user unit, or Task Scheduler)."""
    _run([str(exe), "service", "install"], timeout=60)


def start_now(exe: Path, log_dir: Path) -> None:
    """Start `kanzo --no-open` in the background, detached from Hermes."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log = open(log_dir / "kanzo.log", "ab")
    kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log, "env": kanzo_env()}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen([str(exe), "--no-open"], **kwargs)
    finally:
        log.close()


def join(exe: Path, host: str) -> None:
    host = (host or "").strip()
    host = re.sub(r"^https?://", "", host).rstrip("/")
    if not _HOST_RE.match(host):
        raise SetupError("Enter the address the other computer shows, like 192.168.1.20.")
    _run([str(exe), "join", host], timeout=60)


# --- the agent's tools (Kanzo's MCP server) -----------------------------------------------------


def hermes_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config_readonly
        return load_config_readonly() or {}
    except Exception:
        return {}


def mcp_server(config: Optional[dict] = None) -> Optional[str]:
    """Name of a configured MCP server that is Kanzo's, or None."""
    servers = (hermes_config() if config is None else config).get("mcp_servers") or {}
    for name, entry in servers.items():
        if not isinstance(entry, dict):
            continue
        command = Path(str(entry.get("command") or "")).name.lower()
        args = [str(a) for a in entry.get("args") or []]
        url = str(entry.get("url") or "").rstrip("/")
        if command in ("kanzo", "kanzo.exe") and "mcp" in args:
            return str(name)
        if url.endswith("/mcp") and "kanzo" in str(name).lower():
            return str(name)
    return None


def _hermes() -> list[str]:
    found = shutil.which("hermes")
    return [found] if found else [sys.executable, "-m", "hermes_cli.main"]


def add_mcp(exe: Optional[Path], url: Optional[str], config: Optional[dict] = None) -> str:
    """Add Kanzo's MCP server to Hermes with `hermes mcp add` (all of Kanzo's tools enabled)."""
    config = hermes_config() if config is None else config
    existing = mcp_server(config)
    if existing:
        return existing
    servers = config.get("mcp_servers") or {}
    name = "kanzo" if "kanzo" not in servers else "kanzo-board"
    if exe is not None:
        args = [*_hermes(), "mcp", "add", name, "--command", str(exe), "--args", "mcp"]
    elif url:
        args = [*_hermes(), "mcp", "add", name, "--url", url.rstrip("/") + "/mcp"]
    else:
        raise SetupError("Install Kanzo on this computer first; its MCP server runs from the kanzo program.")
    # `hermes mcp add` asks, in order: for --url only, "Does this server require authentication?"
    # (no: Kanzo has no login); then, once connected, "Enable all N tools? [Y/n/select]", where a
    # blank line enables all. Blank, not "Y": if the server cannot be reached, that second answer
    # goes to "Save config anyway?" instead, and blank keeps its default, which is not to save.
    out = _run(args, timeout=90, stdin="\n" if exe is not None else "n\n\n", hermes=True)
    entry = ((hermes_config().get("mcp_servers") or {}).get(name))
    if not isinstance(entry, dict) or entry.get("enabled") is False:
        lines = [_ANSI_RE.sub("", ln).strip(" ✗⚠") for ln in (out or "").splitlines()]
        reason = next((ln for ln in reversed(lines) if ln.startswith(("Failed", "Cancelled"))), "")
        raise SetupError("Hermes did not save Kanzo's MCP server" + (f": {reason}" if reason else ".")
                         + f" Run `hermes mcp add {name} …` in a terminal to see why.")
    return name
