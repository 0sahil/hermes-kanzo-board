#!/usr/bin/env python3
"""Pin a Kanzo release: rewrite dashboard/kanzo_release.json for a release tag.

    python scripts/update_kanzo_release.py v0.4.3

Reads the release's published sha256.sum and checks each file's checksum against the digest
GitHub's API reports for the same release asset; stops if any of them disagree.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = "emanuele-em/kanzo"
OUT = Path(__file__).resolve().parents[1] / "dashboard" / "kanzo_release.json"
ASSET = re.compile(r"^([0-9a-f]{64}) [ *](kanzo-(.+)\.(tar\.xz|zip))$")


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-kanzo-board", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main(tag: str) -> int:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        print("usage: update_kanzo_release.py vX.Y.Z", file=sys.stderr)
        return 2
    base = f"https://github.com/{REPO}/releases/download/{tag}/"
    api = json.loads(get(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}"))
    digests = {a["name"]: (a.get("digest") or "").removeprefix("sha256:") for a in api.get("assets", [])}
    assets = {}
    for line in get(base + "sha256.sum").decode("utf-8").splitlines():
        m = ASSET.match(line.strip())
        if not m:
            continue
        sha, file, target = m.group(1), m.group(2), m.group(3)
        if digests.get(file) != sha:
            print(f"{file}: sha256.sum says {sha}, GitHub says {digests.get(file)!r}; stopping.", file=sys.stderr)
            return 1
        assets[target] = {"file": file, "sha256": sha}
    if not assets:
        print("No kanzo archives found in sha256.sum; stopping.", file=sys.stderr)
        return 1
    release = {"version": tag[1:], "repository": f"https://github.com/{REPO}", "download_base": base,
               "license": "AGPL-3.0", "assets": dict(sorted(assets.items()))}
    OUT.write_text(json.dumps(release, indent=2) + "\n", "utf-8")
    print(f"Pinned Kanzo {tag[1:]} ({len(assets)} files) in {OUT.relative_to(OUT.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
