# Changelog

All notable changes to Kanzo Board for Hermes are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/0sahil/hermes-kanzo-board/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/0sahil/hermes-kanzo-board/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/0sahil/hermes-kanzo-board/releases/tag/v0.1.0
