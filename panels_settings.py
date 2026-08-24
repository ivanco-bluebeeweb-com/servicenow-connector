"""ServiceNow Connector — App settings panel."""
from __future__ import annotations

from imperal_sdk import ui

import handlers as h
from app import ext


@ext.panel("servicenow_settings", slot="center", title="ServiceNow settings", icon="Settings", center_overlay=True)
async def servicenow_settings(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Text("No ServiceNow instance connected yet.", variant="body")
    rows = []
    for c in connections:
        rows.append(ui.Stack(direction="h", gap=2, align="center", children=[
            ui.Text(f"{c.get('label') or c.get('instance_host', '')} ({c.get('auth_mode', 'basic')})", variant="body"),
            ui.Button("Disconnect", action="disconnect_servicenow", params={"connection_id": c.get("id", "")}, variant="destructive"),
        ]))
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Header(text="Connected instances", level=2),
        *rows,
    ])
