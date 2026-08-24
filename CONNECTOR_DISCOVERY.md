# ServiceNow Connector — Connector Discovery

**Discovery date:** 2026-08-24
**Release scope:** maximum functionality against the publicly documented Now Platform
Table API and its companion REST APIs (per standing "максимальный функционал" instruction).
**Related task:** BBW Imperal Apps #2434.

## 1. What ServiceNow actually is

ServiceNow is a single platform (the **Now Platform**) hosting many modules on top of a
shared database and REST layer: ITSM (Incident, Problem, Change, Request/Catalog,
Knowledge), ITOM, ITAM, CSM, HRSD. Every module's records live in **tables**, and nearly
all of them are reachable through one generic, uniform API — the **Table API** — rather
than dozens of bespoke per-module APIs. This connector targets ITSM's core tables plus
the generic table CRUD surface, which also gives forward compatibility with any other
table a tenant has (CMDB CIs, custom tables, etc.) without needing per-table code.

## 2. Chosen integration surface

**REST Table API**: `https://<instance>.service-now.com/api/now/table/{tableName}`
— supports GET (list/read with encoded query, sysparm_query), POST (create), PUT/PATCH
(update), DELETE. Every ITSM entity (incident, problem, change_request, sc_request,
sc_req_item, change_task, cmdb_ci, sys_user, sys_user_group) is a table.

Companion APIs also targeted:
- **Attachment API** (`/api/now/attachment`) — file attachments on any record.
- **Aggregate API** (`/api/now/stats/{tableName}`) — counts/aggregates for dashboards
  (e.g. open incidents by priority) without pulling full record sets.
- **Batch API** (`/api/now/v1/batch`) — combine several Table API calls into one HTTP
  round trip, used for the connector's own bulk-update wrappers.

Not in scope for v1 (Tier 3, future): Import Set API (bulk staged imports), Service
Catalog structure-definition APIs (creating new catalog items, as opposed to submitting
requests against existing ones), Flow Designer / IntegrationHub APIs.

## 3. Auth model

**OAuth 2.0 (Inbound OAuth, resource owner password credentials or client credentials)**
is ServiceNow's currently recommended integration auth model — an admin registers an
**OAuth API endpoint for external clients** in the instance (System OAuth > Application
Registry), yielding a Client ID + Client Secret. Basic Auth (username/password) against
a scoped integration user is still supported and simpler for smaller tenants, and is
offered as a fallback connect mode since many ServiceNow admins have not set up OAuth.

Both modes require the **instance hostname** (`<instance>.service-now.com`) as a
first-class field — there is no shared multi-tenant endpoint.

## 4. Terminology notes (differs from the rest of the portfolio)

- Every record's primary key is `sys_id` (32-char GUID), not `id`.
- Filtering uses **encoded query strings** (`sysparm_query=active=true^priority=1`),
  not a REST-standard filter param — the connector exposes a raw `query` passthrough
  field for full flexibility, plus typed convenience filters (status, priority, assigned_to)
  for the common cases.
- Related-record fields ("dot-walking", e.g. `caller_id.email`) are supported via
  `sysparm_display_value` and `sysparm_fields` — exposed as optional passthrough params,
  not modeled as nested objects, to avoid guessing tenant-specific dictionary schemas.
- Pagination uses `sysparm_limit` / `sysparm_offset`, and total count requires a
  separate `X-Total-Count` response header read (not a body field) — client handles
  this explicitly.

## 5. Scope decision (Tier 1 = v1)

**Tier 1 (this release):**
- Connect/disconnect (OAuth2 client-credentials OR Basic Auth to instance).
- Incident: list/get/create/update/resolve/close.
- Problem: list/get/create/update.
- Change Request: list/get/create/update, plus state-transition helper.
- Service Catalog Request (sc_request) + Request Item (sc_req_item): list/get/create.
- Knowledge Article (kb_knowledge): list/get.
- CMDB CI (cmdb_ci): list/get (read-focused — CMDB writes are commonly restricted by
  ServiceNow's Discovery/ITOM automation and risky to expose generically).
- Users/Groups (sys_user, sys_user_group): list/get (read-only, for assignment lookups).
- Attachments: list/upload/download on any record.
- Generic table passthrough (list_table_records / get_table_record / create_table_record
  / update_table_record) for any table not explicitly modeled above — this is the
  connector's "escape hatch" so the app stays useful even for tables Discovery didn't
  enumerate, honestly signalling "generic" rather than pretending full coverage.
- Value-add: audit_instance_health (aggregate open incidents by priority/age, overdue
  SLAs where the sla table is reachable, stale problems).

**Tier 2 (future):** Import Set API, Flow Designer triggers, Service Catalog item
definition management, deeper CMDB relationship graph traversal.

## 6. Security notes

- Instance hostname, OAuth client secret / Basic Auth password stored as a single
  encrypted JSON blob per connection (pattern matches SAP/Oracle/Dynamics connectors).
- No destructive default actions — delete_table_record requires explicit confirmation
  semantics matching the rest of the portfolio's `AppSafety` pattern.
