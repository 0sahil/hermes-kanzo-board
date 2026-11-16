# Security policy

## What the plugin can do
Kanzo Board runs inside Hermes. Its backend can read and change your Kanzo board, download and
install the official Kanzo program, start it, and add Kanzo's MCP server to Hermes (each only when
you click for it). The README lists everything it does under "What the plugin does on your
computer".

Built-in protections:
- The board's page runs in Hermes' sandboxed frame with an opaque origin: it cannot reach Hermes,
  its storage, its other plugins or its native bridge. It can only send messages, which the page
  answers for a fixed set of actions (board requests, copy, open an `http(s)` link, save Kanzo's
  settings).
- Board requests are limited to paths on the configured board; the frame cannot use the backend to
  reach any other address.
- The plugin's backend routes sit behind Hermes' own authentication, like every plugin route.
- Kanzo is installed only from its official GitHub release, only after the download matches the
  SHA-256 pinned in `dashboard/kanzo_release.json`, and never over an existing `kanzo` program.
- Join addresses and the board URL are validated before they reach a command or a request; programs
  are started with argument lists, never through a shell.

Not protected against:
- Kanzo has no login. Anyone who can reach a board can read and change it. Keep Kanzo's `listen`
  setting on `127.0.0.1` unless you share the board on a network you trust, and set the plugin's
  Board URL only to boards you trust.
- The agent works on the board through Kanzo's MCP tools, including `delete_task`. Choose its tools
  with `hermes mcp configure kanzo`.

## Reporting a vulnerability
Please **do not** open a public issue. Use GitHub's private
[security advisory form](https://github.com/0sahil/hermes-kanzo-board/security/advisories/new)
instead. You'll get a response within a few days. Please include steps to reproduce and the
versions of the plugin, Hermes and Kanzo.

Vulnerabilities in Kanzo itself should go to the
[Kanzo project](https://github.com/emanuele-em/kanzo/security).

## Supported versions
Only the latest release receives security fixes.
