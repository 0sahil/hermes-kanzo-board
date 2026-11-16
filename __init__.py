"""Kanzo Board for Hermes.

The feature lives in the Desktop page (desktop/plugin.js) and its backend routes
(dashboard/plugin_api.py). register() adds no tools or hooks: the agent's Kanzo
tools come from Kanzo's own MCP server, which the page can add to Hermes.
"""


def register(ctx) -> None:  # noqa: ARG001
    return None
