# Kanzo for Hermes Desktop

Adds a **Kanzo** entry to the Hermes Desktop sidebar that opens your
[Kanzo](https://github.com/emanuele-em/kanzo) board — the self-hosted kanban for
humans and agents by [Emanuele](https://github.com/emanuele-em) — right inside
the app. It is Kanzo's own web UI, running from your own board: same look, same
keyboard shortcuts, drag and drop, task panel, search, filters, settings.

Unofficial community plugin; not affiliated with or endorsed by the Kanzo project.

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

Kanzo sends `frame-ancestors 'none'`, so its page can't simply be embedded. The
plugin instead:

1. fetches the board's own `index.html` and `app.js` from **your** running Kanzo
   (`dashboard/plugin_api.py`, `dashboard/frame.py`) — nothing of Kanzo is
   bundled in this repository;
2. shows them in Hermes' sandboxed frame (`SandboxedFrame`, opaque origin);
3. puts a small bridge (`dashboard/bridge.js`) in front of `app.js` for what the
   sandbox takes away: the board's requests go through the plugin backend,
   `localStorage` is kept by the plugin, `confirm()` becomes an in-frame dialog,
   and links/copy go through the Hermes app.

Because the UI comes from your board, it always matches your Kanzo version.
Nothing leaves your machine except what Kanzo itself does.

## Notes

- Kanzo has no login; anyone who can reach the board can edit it, and so can
  this plugin. Point `KANZO_URL` only at boards you trust.
- The bridge adapts Kanzo's current web UI (0.4.x). A future Kanzo release that
  changes how its page is built may need a plugin update; if the `confirm()`
  adaptation fails, confirmations safely answer *Cancel*.
- Images and the translation file load directly from the board URL, so the
  machine running Hermes Desktop must be able to reach it.
- Hermes' own shortcuts (⌘K etc.) don't fire while the board has focus — the
  board's shortcuts do, as in Kanzo.

## License

This plugin: MIT. Kanzo is © its authors under
[AGPL-3.0](https://github.com/emanuele-em/kanzo/blob/main/LICENSE) and is not
distributed here.
