# ServiceNow Connector — Preparation

**Version:** 0.1.0 (planning)
**Date:** 2026-08-24
**Related task:** BBW Imperal Apps #2434
**Scope decision:** maximum feasible capability against the publicly documented Now
Platform Table API (per standing "максимальный функционал" instruction).

## 1. App passport

**Name:** ServiceNow Connector
**One-line purpose:** Connect your own ServiceNow instance (OAuth2 or Basic Auth) to
manage Incidents, Problems, Change Requests, Service Catalog Requests, Knowledge
Articles, and CMDB CIs through the Now Platform Table API, plus a generic table
passthrough for anything else your instance exposes.

**What it is not:**
- Not a Flow Designer / IntegrationHub replacement — no workflow orchestration inside
  ServiceNow itself.
- Not an Import Set / bulk-migration tool — that's Tier 2/future scope.
- Does not model every ServiceNow table with typed schemas (there can be thousands per
  tenant with heavy customization) — ITSM's Tier-1 tables get typed wrappers; everything
  else is reachable through the honest generic table passthrough.

## 2. Human problem

> An IT service desk agent, ITSM admin, or ops engineer at a company running
> ServiceNow needs a fast way to look up, create, and update incidents/problems/changes/
> requests without opening the ServiceNow UI — especially for quick triage, bulk status
> updates, or pulling a health snapshot for a stand-up.

### Personas
| Persona | Trigger | Value |
|---|---|---|
| Service desk agent | "What's the status of INC0012345?" | Instant lookup without switching to ServiceNow UI |
| ITSM admin | Needs to bulk-update a batch of stale incidents | Bulk wrapper over Table API + Batch API |
| Ops engineer | Wants a daily health snapshot (open P1s, overdue SLAs) | audit_instance_health value-add report |
| Change manager | Needs to see change requests awaiting approval | list_change_requests with state filter |

## 3. Capability tiers

**Tier 1 (this release — full commitment per "максимум"):**
- connect_servicenow / disconnect_servicenow / list_connections
- Incident: list, get, create, update, resolve_incident, close_incident
- Problem: list, get, create, update
- Change Request: list, get, create, update, set_change_state (new/assess/authorize/
  scheduled/implement/review/closed)
- Service Catalog: list_catalog_requests, get_catalog_request, create_catalog_request,
  list_request_items
- Knowledge: list_knowledge_articles, get_knowledge_article
- CMDB: list_cis, get_ci (read-only)
- Users/Groups: list_users, list_groups (read-only, for assignment)
- Attachments: list_attachments, upload_attachment, get_attachment_download_url
- Generic table passthrough: list_table_records, get_table_record, create_table_record,
  update_table_record, delete_table_record (explicit table_name param — the honest
  escape hatch for anything not typed above)
- Value-add: audit_instance_health (open incidents by priority, overdue SLA count if
  reachable, stale problems > N days)
- Bulk: bulk_update_incidents (via Batch API), bulk_close_incidents

**Tier 2 (future):** Import Set API, Service Catalog item authoring, deeper CMDB
relationship traversal, Flow Designer trigger integration.

## 4. Auth & security

Two connect modes, matching Discovery §3:
1. **OAuth2** (client_id + client_secret, resource-owner-password or client-credentials
   grant against `<instance>.service-now.com/oauth_token.do`).
2. **Basic Auth** (username + password against a scoped integration user) — simpler
   fallback, many ServiceNow tenants use this for API integrations.

Both require explicit `instance_url` (no shared multi-tenant endpoint). Credentials
stored as one encrypted JSON blob per connection, following the SAP/Oracle/Dynamics/
Infor connector pattern already in the portfolio.

No destructive-by-default actions. `delete_table_record` exists (needed for the
generic passthrough to be genuinely useful) but is clearly flagged in its own
description as irreversible, matching `APP_SAFETY_CHECKLIST.md`.

## 5. Pricing intent (set before submission per standing rule)

Read-heavy tools (list/get) priced modestly; write tools (create/update/resolve/close)
priced higher; audit/aggregate report priced at a premium tier; connect/disconnect/
list_connections free — mirrors the pricing shape already applied to SAP/Oracle/
Dynamics/Infor connectors.
