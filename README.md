# Kanzo for Hermes Desktop

Adds a **Kanzo** entry to the Hermes Desktop sidebar that shows your
[Kanzo](https://github.com/emanuele-em/kanzo) board (a self-hosted kanban for
humans and agents) inside the app: projects sidebar, status columns, cards with
tags, a filter box, task details with comments, and drag-to-move between columns.

Unofficial community plugin; not affiliated with the Kanzo project.

## Requirements

- Hermes Desktop
- A running Kanzo board (`kanzo`, default http://127.0.0.1:4242)

## Install

```bash
hermes plugins install <owner>/hermes-kanzo --enable
```

Then in the desktop app press ⌘K → **Reload desktop plugins**, and make sure
the plugin is switched on under Settings → Capabilities → Plugins.

## Configuration

The backend finds the board in this order:

1. `KANZO_URL` (e.g. `http://192.168.1.20:4242` for a shared board)
2. the `port` in `$KANZO_HOME/config.toml` (default `~/kanzo`), on `127.0.0.1`
3. `http://127.0.0.1:4242`

Set `KANZO_URL` in `~/.hermes/.env`, then restart the gateway.

## How it works

Kanzo sends `frame-ancestors 'none'`, so its page cannot be embedded. The plugin
instead renders the board natively and talks to Kanzo's local HTTP API through a
small backend (`dashboard/plugin_api.py`): `GET /board`, `GET /task/{id}`,
`POST /move`. Nothing leaves your machine.

## Notes

- Kanzo has no login; anyone who can reach the board can edit it, and so can
  this plugin. Point `KANZO_URL` only at boards you trust.
- Creating/editing tasks is not implemented yet: use the Kanzo web UI or its MCP server.
- Kanzo's HTTP API is not a documented stable interface; a Kanzo update may require a plugin update.

## License

MIT
