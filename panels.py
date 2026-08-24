"""ServiceNow Connector panels."""
from __future__ import annotations

from imperal_sdk import ui

import handlers as h
from app import ext


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="label"),
        node,
    ])


@ext.panel("servicenow_sidebar", slot="left", title="ServiceNow")
async def servicenow_sidebar(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Text("Connect your ServiceNow instance", variant="subtitle"),
            ui.Form(action="connect_servicenow", submit_label="Connect", children=[
                _field("Instance label", ui.Input(param_name="label", placeholder="Acme Production")),
                _field("Instance host", ui.Input(param_name="instance_host", placeholder="acme.service-now.com")),
                _field("Auth mode", ui.Select(param_name="auth_mode", options=["basic", "oauth2"], value="basic")),
                _field("Username", ui.Input(param_name="username", placeholder="integration.user")),
                _field("Password", ui.Input(param_name="password", placeholder="Integration user password")),
                _field("OAuth client ID (if OAuth2)", ui.Input(param_name="client_id", placeholder="Application Registry client ID")),
                _field("OAuth client secret (if OAuth2)", ui.Input(param_name="client_secret", placeholder="Application Registry client secret")),
            ]),
            ui.Button("How do I get this?", variant="ghost", size="sm", icon="HelpCircle",
                      on_click=ui.Call("__panel__servicenow_connect_help")),
        ])
    conn = connections[0]
    label = conn.get("label") or conn.get("instance_host", "")
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Text(label, variant="subtitle"),
        ui.Divider(),
        ui.Button("Incidents", variant="ghost", full_width=True, on_click=ui.Call("__panel__servicenow_center", view="incidents")),
        ui.Button("Problems", variant="ghost", full_width=True, on_click=ui.Call("__panel__servicenow_center", view="problems")),
        ui.Button("Change requests", variant="ghost", full_width=True, on_click=ui.Call("__panel__servicenow_center", view="changes")),
        ui.Button("Service requests", variant="ghost", full_width=True, on_click=ui.Call("__panel__servicenow_center", view="requests")),
        ui.Button("Knowledge base", variant="ghost", full_width=True, on_click=ui.Call("__panel__servicenow_center", view="knowledge")),
        ui.Button("CMDB", variant="ghost", full_width=True, on_click=ui.Call("__panel__servicenow_center", view="cmdb")),
        ui.Divider(),
        ui.Button("App settings", variant="ghost", full_width=True, icon="settings", on_click=ui.Call("__panel__servicenow_settings")),
    ])


@ext.panel("servicenow_connect_help", slot="overlay", title="Connecting ServiceNow")
async def servicenow_connect_help(ctx, **kwargs) -> ui.UINode:
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Header(text="How to connect ServiceNow", level=2),
        ui.Text("Basic Auth: create (or reuse) an integration user in your instance with the rest_api_explorer and itil roles, then use its username/password here.", variant="body"),
        ui.Text("OAuth2: in your instance go to System OAuth > Application Registry, create an OAuth API endpoint for external clients, and use the generated client ID/secret plus an integration user's username/password.", variant="body"),
        ui.Text("Instance host is the part before '.service-now.com', e.g. 'acme' for acme.service-now.com \u2014 enter the full host including the domain.", variant="body"),
        ui.Callout(text="Credentials are stored encrypted and used only to call your instance's Table API on your behalf.", type="info"),
    ])


@ext.panel("servicenow_center", slot="center", title="ServiceNow", icon="Ticket", center_overlay=True)
async def servicenow_center(ctx, view: str = "incidents", **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Text("Connect a ServiceNow instance first.", variant="body")

    if view == "problems":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Problems", level=2),
            ui.Form(action="list_problems", submit_label="Refresh", children=[
                _field("State filter (optional)", ui.Input(param_name="state", placeholder="1 = Open, 3 = Closed/Resolved")),
            ]),
            ui.Divider(),
            ui.Text("New problem", variant="subtitle"),
            ui.Form(action="create_problem", submit_label="Create problem", children=[
                _field("Short description", ui.Input(param_name="short_description", placeholder="Recurring VPN disconnects across EU region")),
                _field("Description", ui.Textarea(param_name="description", placeholder="Root cause investigation notes so far...")),
            ]),
        ])

    if view == "changes":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Change requests", level=2),
            ui.Form(action="list_change_requests", submit_label="Refresh", children=[
                _field("State filter (optional)", ui.Input(param_name="state", placeholder="-5 = New, 0 = Scheduled, 3 = Closed")),
                _field("Approval filter (optional)", ui.Select(param_name="approval", options=["", "requested", "approved", "rejected"], value="")),
            ]),
            ui.Divider(),
            ui.Text("New change request", variant="subtitle"),
            ui.Form(action="create_change_request", submit_label="Create change", children=[
                _field("Short description", ui.Input(param_name="short_description", placeholder="Upgrade production database cluster to v15")),
                _field("Description", ui.Textarea(param_name="description", placeholder="Change plan, rollback steps, maintenance window...")),
                _field("Type", ui.Select(param_name="type", options=["standard", "normal", "emergency"], value="normal")),
            ]),
        ])

    if view == "requests":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Service Catalog requests", level=2),
            ui.Form(action="list_requests", submit_label="Refresh", children=[
                _field("State filter (optional)", ui.Input(param_name="state", placeholder="1 = Requested, 3 = Closed Complete")),
            ]),
            ui.Divider(),
            ui.Text("New request", variant="subtitle"),
            ui.Form(action="create_request", submit_label="Create request", children=[
                _field("Short description", ui.Input(param_name="short_description", placeholder="New laptop for onboarding employee")),
                _field("Description", ui.Textarea(param_name="description", placeholder="Item, quantity, delivery location...")),
            ]),
        ])

    if view == "knowledge":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Knowledge base", level=2),
            ui.Form(action="list_knowledge_articles", submit_label="Search", children=[
                _field("Search text (optional)", ui.Input(param_name="query", placeholder="VPN setup instructions")),
            ]),
        ])

    if view == "cmdb":
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Header(text="Configuration Management Database", level=2),
            ui.Form(action="list_cmdb_cis", submit_label="Refresh", children=[
                _field("CI class (optional)", ui.Input(param_name="ci_class", placeholder="cmdb_ci_server")),
            ]),
        ])

    # default: incidents
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Header(text="Incidents", level=2, subtitle="Live view of your ServiceNow instance"),
        ui.Form(action="list_incidents", submit_label="Refresh", children=[
            _field("State filter (optional)", ui.Input(param_name="state", placeholder="1 = New, 2 = In Progress, 6 = Resolved")),
            _field("Priority filter (optional)", ui.Select(param_name="priority", options=["", "1", "2", "3", "4", "5"], value="")),
        ]),
        ui.Divider(),
        ui.Text("New incident", variant="subtitle"),
        ui.Form(action="create_incident", submit_label="Create incident", children=[
            _field("Short description", ui.Input(param_name="short_description", placeholder="Email server unreachable from EU office")),
            _field("Description", ui.Textarea(param_name="description", placeholder="Steps to reproduce, affected users, timeline...")),
            _field("Urgency", ui.Select(param_name="urgency", options=["1", "2", "3"], value="3")),
            _field("Impact", ui.Select(param_name="impact", options=["1", "2", "3"], value="3")),
        ]),
        ui.Divider(),
        ui.Text("Instance health", variant="subtitle"),
        ui.Button("Run health audit", variant="secondary", on_click=ui.Call("audit_instance_health")),
    ])
