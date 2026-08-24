"""ServiceNow Connector extension declaration.

ServiceNow is the Now Platform: a single shared table-based database and REST
layer underneath many modules (ITSM, ITOM, ITAM, CSM). This connector targets
the Table API's ITSM core (Incident, Problem, Change, Request, Knowledge, CMDB)
plus a generic table passthrough for anything else a tenant exposes.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "servicenow-connector",
    version="0.1.0",
    display_name="ServiceNow",
    description=(
        "Connect your own ServiceNow instance (OAuth2 or Basic Auth) to manage "
        "Incidents, Problems, Change Requests, Service Catalog Requests, Knowledge "
        "Articles, and CMDB CIs through the Now Platform Table API, plus a generic "
        "table passthrough for anything else your instance exposes."
    ),
    icon="icon.svg",
    capabilities=["servicenow:read", "servicenow:write"],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="servicenow",
    description=(
        "ServiceNow Connector — manage Incidents, Problems, Changes, Requests, "
        "Knowledge, and CMDB records through the Now Platform Table API."
    ),
)

ext.secret(
    "servicenow_connections",
    "JSON list of connected ServiceNow instances and encrypted credentials. Managed only through connect_servicenow and disconnect_servicenow.",
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=90,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Report whether at least one ServiceNow instance is configured."""
    raw = await ctx.secrets.get("servicenow_connections")
    import json
    try:
        connections = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        connections = []
    if not connections:
        return {"status": "not_configured", "message": "No ServiceNow instance connected yet."}
    return {"status": "ok", "message": f"{len(connections)} ServiceNow instance(s) connected."}
