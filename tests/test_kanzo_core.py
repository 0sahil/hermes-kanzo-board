import hashlib
import io
import json
import os
import stat
import tarfile
import zipfile

import pytest

import kanzo_core as core


# --- the board's address ---------------------------------------------------------------------------


def test_board_url_prefers_the_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("KANZO_HOME", str(tmp_path))
    assert core.board_url({"board_url": "http://192.168.1.20:4242/"}) == ("http://192.168.1.20:4242", "setting")


def test_board_url_uses_the_local_port(tmp_path, monkeypatch):
    monkeypatch.setenv("KANZO_HOME", str(tmp_path))
    (tmp_path / "config.toml").write_text('# Kanzo settings\nport = 4300  # mine\nlisten = "127.0.0.1"\n')
    assert core.board_url({}) == ("http://127.0.0.1:4300", "local")


def test_board_url_defaults_to_4242(tmp_path, monkeypatch):
    monkeypatch.setenv("KANZO_HOME", str(tmp_path / "missing"))
    assert core.board_url({"board_url": "  "}) == ("http://127.0.0.1:4242", "local")


@pytest.mark.parametrize("bad", ["192.168.1.20:4242", "ftp://host", "http://host/path", "http://user@host",
                                 "javascript:alert(1)", "http://host?x=1"])
def test_board_url_rejects_anything_but_an_origin(bad):
    with pytest.raises(core.SetupError):
        core.normalize_url(bad)


@pytest.mark.parametrize("path", ["http://evil.example/", "//evil.example/x", "api/board", "/a\r\nHost: x", "\\x"])
def test_board_request_only_reaches_the_board(path):
    with pytest.raises(core.SetupError):
        core.board_request("http://127.0.0.1:1", "GET", path)


# --- installing Kanzo ------------------------------------------------------------------------------


@pytest.mark.parametrize("system,machine,expected", [
    ("Darwin", "arm64", "aarch64-apple-darwin"),
    ("Darwin", "x86_64", "x86_64-apple-darwin"),
    ("Linux", "x86_64", "x86_64-unknown-linux-musl"),
    ("Linux", "aarch64", "aarch64-unknown-linux-musl"),
    ("Linux", "armv7l", "armv7-unknown-linux-musleabihf"),
    ("Linux", "armv6l", "arm-unknown-linux-musleabihf"),
    ("Windows", "AMD64", "x86_64-pc-windows-msvc"),
    ("Windows", "ARM64", None),
    ("FreeBSD", "amd64", None),
])
def test_target(system, machine, expected):
    assert core.target(system, machine) == expected


def test_pinned_release_covers_every_target():
    rel = core.release()
    assert rel["download_base"].startswith("https://github.com/emanuele-em/kanzo/releases/download/v")
    assert rel["download_base"].rstrip("/").endswith("v" + rel["version"])
    for system, machine in [("Darwin", "arm64"), ("Darwin", "x86_64"), ("Linux", "x86_64"), ("Linux", "aarch64"),
                            ("Linux", "armv7l"), ("Linux", "armv6l"), ("Windows", "AMD64")]:
        asset = rel["assets"][core.target(system, machine)]
        assert len(asset["sha256"]) == 64 and int(asset["sha256"], 16) >= 0


def _tar(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


@pytest.fixture
def fake_release(tmp_path, monkeypatch):
    """Point the plugin at a release whose only asset (this computer's target) is `archive`."""
    def make(archive, *, name=None, digest=None):
        tgt = core.target() or "x86_64-unknown-linux-musl"
        monkeypatch.setattr(core, "target", lambda *a: tgt)
        name = name or f"kanzo-{tgt}.tar.xz"
        rel = {"version": "9.9.9", "repository": "https://example.invalid", "download_base": "https://example.invalid/",
               "assets": {tgt: {"file": name, "sha256": digest or hashlib.sha256(archive).hexdigest()}}}
        path = tmp_path / "release.json"
        path.write_text(json.dumps(rel))
        monkeypatch.setattr(core, "RELEASE_FILE", path)
        return lambda url: archive
    return make


def test_install_writes_an_executable_program(tmp_path, fake_release):
    fetch = fake_release(_tar({"kanzo-x/README.md": b"readme", f"kanzo-x/{core.EXE}": b"#!/bin/sh\necho kanzo 9.9.9\n"}))
    dest = core.install_kanzo(tmp_path / "bin", fetch=fetch)
    assert dest == tmp_path / "bin" / core.EXE
    assert dest.read_bytes().startswith(b"#!/bin/sh")
    if os.name != "nt":
        assert dest.stat().st_mode & stat.S_IXUSR
    assert sorted(p.name for p in (tmp_path / "bin").iterdir()) == [core.EXE]


def test_install_reads_a_zip(tmp_path, fake_release, monkeypatch):
    archive = _zip({f"kanzo-x/{core.EXE}": b"program"})
    fetch = fake_release(archive, name="kanzo-x86_64-pc-windows-msvc.zip")
    assert core.install_kanzo(tmp_path / "bin", fetch=fetch).read_bytes() == b"program"


def test_install_refuses_a_checksum_mismatch(tmp_path, fake_release):
    fetch = fake_release(_tar({f"kanzo-x/{core.EXE}": b"program"}), digest="0" * 64)
    with pytest.raises(core.SetupError, match="checksum"):
        core.install_kanzo(tmp_path / "bin", fetch=fetch)
    assert not (tmp_path / "bin").exists()


def test_install_never_extracts_other_paths(tmp_path, fake_release):
    fetch = fake_release(_tar({"../../evil": b"x", f"kanzo-x/{core.EXE}": b"program"}))
    core.install_kanzo(tmp_path / "a" / "bin", fetch=fetch)
    assert not (tmp_path / "evil").exists()
    assert [p.name for p in (tmp_path / "a" / "bin").iterdir()] == [core.EXE]


def test_install_needs_exactly_one_program(tmp_path, fake_release):
    fetch = fake_release(_tar({"kanzo-x/README.md": b"no program"}))
    with pytest.raises(core.SetupError, match="one kanzo program"):
        core.install_kanzo(tmp_path / "bin", fetch=fetch)


def test_install_does_not_replace_an_existing_kanzo(tmp_path, fake_release):
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / core.EXE).write_bytes(b"theirs")
    fetch = fake_release(_tar({f"kanzo-x/{core.EXE}": b"ours"}))
    with pytest.raises(core.SetupError, match="already exists"):
        core.install_kanzo(tmp_path / "bin", fetch=fetch)
    assert (tmp_path / "bin" / core.EXE).read_bytes() == b"theirs"


def test_install_dir_follows_cargo_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CARGO_HOME", str(tmp_path / "cargo"))
    assert core.install_dir() == tmp_path / "cargo" / "bin"


# --- joining and the agent's tools ---------------------------------------------------------------


@pytest.mark.parametrize("host", ["192.168.1.20", "192.168.1.20:4242", "http://pi.local:4242/", "[fd00::1]:4242", "my-pi"])
def test_join_accepts_addresses(host, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(core, "_run", lambda args, **kw: calls.append(args) or "")
    core.join(tmp_path / "kanzo", host)
    assert calls[0][1] == "join" and "/" not in calls[0][2]


@pytest.mark.parametrize("host", ["", "a b", "--help", "host;rm -rf /", "-x"])
def test_join_rejects_anything_else(host, tmp_path):
    with pytest.raises(core.SetupError):
        core.join(tmp_path / "kanzo", host)


def test_mcp_server_finds_kanzo():
    assert core.mcp_server({"mcp_servers": {"tasks": {"command": "/Users/me/.cargo/bin/kanzo", "args": ["mcp"]}}}) == "tasks"
    assert core.mcp_server({"mcp_servers": {"kanzo-pi": {"url": "http://pi:4242/mcp"}}}) == "kanzo-pi"
    assert core.mcp_server({"mcp_servers": {"github": {"command": "npx", "args": ["gh-mcp"]}}}) is None
    assert core.mcp_server({}) is None


def test_add_mcp_runs_hermes_mcp_add(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(core, "_hermes", lambda: ["hermes"])
    monkeypatch.setattr(core, "_run", lambda args, **kw: calls.append((args, kw)) or "")
    assert core.add_mcp(tmp_path / "kanzo", None, config={}) == "kanzo"
    args, kw = calls[0]
    assert args == ["hermes", "mcp", "add", "kanzo", "--command", str(tmp_path / "kanzo"), "--args", "mcp"]
    assert kw["stdin"] == "Y\n"


def test_add_mcp_uses_http_for_a_board_elsewhere(monkeypatch):
    calls = []
    monkeypatch.setattr(core, "_hermes", lambda: ["hermes"])
    monkeypatch.setattr(core, "_run", lambda args, **kw: calls.append(args) or "")
    core.add_mcp(None, "http://pi:4242", config={"mcp_servers": {"kanzo": {"command": "other"}}})
    assert calls[0] == ["hermes", "mcp", "add", "kanzo-board", "--url", "http://pi:4242/mcp"]


def test_add_mcp_keeps_an_existing_server(monkeypatch):
    monkeypatch.setattr(core, "_run", lambda *a, **k: pytest.fail("should not run"))
    config = {"mcp_servers": {"board": {"command": "kanzo", "args": ["mcp"]}}}
    assert core.add_mcp(None, None, config=config) == "board"
