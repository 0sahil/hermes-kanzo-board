# Changelog

All notable changes to Kanzo Board for Hermes are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.2] - 2026-11-17

### Security
- `kanzo` now runs with a minimal environment instead of Hermes' full one, so Hermes' provider
  keys never reach it or the board started with **Start once**.

### Fixed
- **Add Kanzo tools** for a board on another computer: `hermes mcp add` asks about authentication
  first, which used up the answer meant for "Enable all tools?", so nothing was saved while the
  page reported success. Each prompt now gets its own answer, and the page checks that Hermes saved
  the server before saying it did.
- `kanzo.log` goes to the active profile's Hermes home.

## [0.1.1] - 2026-11-17

### Fixed
- When the board stops answering while the page is open, the page now switches to setup at once
  instead of leaving Kanzo's "Board not reachable" view up until the next status check.

### Added
- Screenshots in the README.

## [0.1.0] - 2026-11-17

First public release.

### Added
- A **Kanzo** page in the Hermes Desktop sidebar that runs your board's own web UI, inside Hermes'
  sandboxed frame, so it looks and works like Kanzo in a browser.
- Setup from the page when no board answers: install the official Kanzo release (0.4.2, checked
  against a pinned SHA-256), start the board at login (`kanzo service install`) or once, or join a
  board another computer shares (`kanzo join`).
- **Board URL** setting for a board on another computer or server.
- **Add Kanzo tools**: adds Kanzo's MCP server to Hermes so the agent can work on the board.
- ⌘K command "Open Kanzo board".

[Unreleased]: https://github.com/0sahil/hermes-kanzo-board/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/0sahil/hermes-kanzo-board/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/0sahil/hermes-kanzo-board/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/0sahil/hermes-kanzo-board/releases/tag/v0.1.0
