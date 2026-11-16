# Contributing to Kanzo Board for Hermes

Thanks for your interest! Bug reports, ideas and pull requests are all welcome.

## Before you start
- For anything bigger than a small fix, please open an issue first so we can agree on the approach.
- Check existing issues to avoid duplicates.
- Problems with the board itself (columns, tasks, Kanzo's MCP tools) belong in
  [Kanzo's issues](https://github.com/emanuele-em/kanzo/issues). This repository is only the Hermes
  side.

## Development setup
Requirements: Hermes Desktop 0.23.1 or newer, Python 3.9+, Node.js (for a syntax check), and Kanzo
(or let the plugin install it).

```sh
git clone https://github.com/0sahil/hermes-kanzo-board.git
cd hermes-kanzo-board
python -m pip install pytest
python -m pytest                       # unit tests
hermes plugins validate .              # the check the Hermes plugin catalog runs
```

To try your changes in Hermes, install your checkout over the installed copy:

```sh
hermes plugins install "file://$PWD" --force --enable
hermes gateway restart                 # the backend (dashboard/*.py) only reloads on a restart
```

The page (`desktop/plugin.js`) reloads with **⌘K → Reload desktop plugins**.

## Project layout
- `plugin.yaml`: the plugin manifest (name, version, `requires_hermes`, settings).
- `desktop/plugin.js`: the Desktop page, setup screen and sidebar entry. Plain ESM loaded without a
  build step; it may import only `@hermes/plugin-sdk`, `react` and `react/jsx-runtime`.
- `dashboard/plugin_api.py`: the backend routes, mounted at `/api/plugins/kanzo-board/`.
- `dashboard/kanzo_core.py`: finding, installing, starting and joining Kanzo, and adding its MCP
  server. No web framework, so it is tested on its own.
- `dashboard/frame.py` and `dashboard/bridge.js`: build the board page that runs in the sandboxed
  frame (see "How it works" in the README).
- `dashboard/kanzo_release.json`: the Kanzo release the plugin installs, with a SHA-256 per file.
- `tests/`: unit tests for the backend modules.

## Updating the pinned Kanzo release
When Kanzo publishes a new release, regenerate the pin from its published checksums:

```sh
python scripts/update_kanzo_release.py v0.4.3
```

The script reads the release's `sha256.sum`, checks every file against the digest GitHub reports
for it, and rewrites `dashboard/kanzo_release.json`. Review the diff, install it on a real machine
once, and mention the new version in `CHANGELOG.md`.

## Pull requests
- Keep PRs focused; one change per PR.
- Add or update tests for backend changes.
- Make sure `python -m pytest` and `hermes plugins validate .` pass (CI runs both, on macOS, Linux
  and Windows).
- For changes to the page, include a screenshot or short recording.
- Add a line under `## [Unreleased]` in `CHANGELOG.md`.
- Anything new the plugin does on the user's computer (a program it runs, a file it writes, a
  network call) must be listed under "What the plugin does on your computer" in the README.

## Ground rules for the code
These keep the plugin acceptable for the Hermes plugin catalog:
- `desktop/plugin.js` uses only the plugin SDK: no `eval` or `new Function`, no `<script>`
  injection, no reaching into Hermes' own markup or stores. Anything that has to run inside the
  board page goes in `dashboard/bridge.js`, which runs only in the sandboxed frame.
- No self-updating: the plugin never replaces its own files.
- Kanzo is downloaded only from its official releases and only with a pinned checksum. Never add
  Kanzo's code or program to this repository.
- Nothing runs unless the user clicks for it, and nothing waits for input that might never come.

## License
By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
