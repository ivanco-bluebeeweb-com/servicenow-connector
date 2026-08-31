"""Chat functions for ServiceNow Connector (Now Platform Table API)."""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import servicenow_client as sc
from app import chat
from schemas import (
    Attachment, BulkOutcome, ChangeRequest, ChangeRequestList, CmdbCI, CmdbCIList,
    ConnectServiceNowParams, ConnectionList, ConnectionRefParams, CreateChangeParams,
    CreateIncidentParams, CreateProblemParams, CreateRecordParams, CreateRequestParams,
    DeleteRecordParams, DeleteResult, DisconnectServiceNowParams, GetRecordParams,
    HealthAudit, Incident, IncidentList, KnowledgeArticle, KnowledgeArticleList,
    ListCmdbParams, ListChangeParams, ListIncidentsParams, ListKnowledgeParams,
    ListProblemsParams, ListRequestsParams, ListTableParams, NoParams, Problem,
    ProblemList, ServiceCatalogRequest, ServiceCatalogRequestList, ServiceNowConnection,
    SysIdParams, TableRecord, TableRecordList, UpdateChangeParams, UpdateIncidentParams,
    UpdateProblemParams, UpdateRecordParams, UpdateRequestParams,
)

_SECRET_NAME = "servicenow_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _connection_entity(connection: dict) -> ServiceNowConnection:
    label = connection.get("label") or connection.get("instance_host", "")
    return ServiceNowConnection(
        id=connection.get("id", ""), title=label, label=label,
        instance_host=connection.get("instance_host", ""),
        auth_mode=connection.get("auth_mode", "basic"), connected=True,
    )


def _find_connection(connections: list[dict], connection_id: str) -> dict | None:
    if not connections:
        return None
    if not connection_id:
        return connections[0]
    for c in connections:
        if c.get("id") == connection_id:
            return c
    return None


def _client_for(record: dict) -> sc.ServiceNowClient:
    return sc.ServiceNowClient(
        instance_host=record.get("instance_host", ""),
        auth_mode=record.get("auth_mode", "basic"),
        username=record.get("username", ""),
        password=record.get("password", ""),
        client_id=record.get("client_id", ""),
        client_secret=record.get("client_secret", ""),
    )


async def _resolve_client(ctx, connection_id: str) -> tuple[dict, sc.ServiceNowClient]:
    connections = await _load_connections(ctx)
    record = _find_connection(connections, connection_id)
    if not record:
        raise sc.ServiceNowError("No ServiceNow instance is connected. Connect one first.")
    return record, _client_for(record)


def _record_to_incident(item: dict) -> Incident:
    return Incident(
        sys_id=str(item.get("sys_id", "")), title=item.get("number", "") or str(item.get("sys_id", "")),
        number=item.get("number", ""), short_description=item.get("short_description", ""),
        state=str(item.get("state", "")), priority=str(item.get("priority", "")),
        urgency=str(item.get("urgency", "")), impact=str(item.get("impact", "")),
        assigned_to=str(item.get("assigned_to", "") or ""), raw=item,
    )


@chat.function("connect_servicenow", "Connect a ServiceNow instance via OAuth2 or Basic Auth, after validating connectivity.", action_type="write", chain_callable=True, data_model=ServiceNowConnection, event="servicenow-connector.connect_servicenow", effects=["servicenow.provider.connected"])
async def connect_servicenow(ctx, params: ConnectServiceNowParams) -> ActionResult:
    """Imperal action: connect_servicenow."""
    if params.auth_mode == "oauth2":
        if not all((params.client_id, params.client_secret, params.username, params.password)):
            return ActionResult.error("OAuth2 mode requires client ID, client secret, username, and password.", code="SNOW_MISSING_OAUTH_FIELDS")
    else:
        if not all((params.username, params.password)):
            return ActionResult.error("Basic Auth mode requires username and password.", code="SNOW_MISSING_BASIC_FIELDS")

    record = {
        "instance_host": params.instance_host, "auth_mode": params.auth_mode,
        "username": params.username, "password": params.password,
        "client_id": params.client_id, "client_secret": params.client_secret,
    }
    client = _client_for(record)
    try:
        await client.ping()
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_CONNECT_FAILED", retryable=exc.retryable)

    record.update({"id": str(uuid.uuid4()), "label": params.label or params.instance_host})
    connections = await _load_connections(ctx)
    connections.append(record)
    await _save_connections(ctx, connections)
    return ActionResult.success(data=_connection_entity(record), summary="ServiceNow instance connection was verified and saved.")


@chat.function("disconnect_servicenow", "Disconnect a ServiceNow instance: deletes only the saved credentials. Nothing in ServiceNow itself is changed.", action_type="write", chain_callable=True, data_model=DeleteResult, event="servicenow-connector.disconnect_servicenow", effects=["servicenow.provider.disconnected"])
async def disconnect_servicenow(ctx, params: DisconnectServiceNowParams) -> ActionResult:
    """Imperal action: disconnect_servicenow."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    await _save_connections(ctx, remaining)
    return ActionResult.success(data=DeleteResult(id=params.connection_id, title="ServiceNow connection", deleted=len(remaining) != len(connections)), summary="Servicenow disconnected.")


@chat.function("list_connections", "List the connected ServiceNow instances.", action_type="read", chain_callable=True, data_model=ConnectionList, event="servicenow-connector.list_connections")
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Imperal action: list_connections."""
    connections = await _load_connections(ctx)
    return ActionResult.success(data=ConnectionList(connections=[_connection_entity(c) for c in connections]), summary="Connections listed.")


@chat.function("list_incidents", "List incidents in the connected ServiceNow instance, optionally filtered by state/priority/assignee.", action_type="read", chain_callable=True, data_model=IncidentList, event="servicenow-connector.list_incidents")
async def list_incidents(ctx, params: ListIncidentsParams) -> ActionResult:
    """Imperal action: list_incidents."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        clauses = []
        if params.state:
            clauses.append(f"state={params.state}")
        if params.priority:
            clauses.append(f"priority={params.priority}")
        if params.assigned_to:
            clauses.append(f"assigned_to={params.assigned_to}")
        items = await client.list_table("incident", query="^".join(clauses), limit=params.limit)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_LIST_INCIDENTS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=IncidentList(incidents=[_record_to_incident(i) for i in items]), summary="Incidents listed.")


@chat.function("get_incident", "Read one incident in full by sys_id.", action_type="read", chain_callable=True, data_model=Incident, event="servicenow-connector.get_incident")
async def get_incident(ctx, params: SysIdParams) -> ActionResult:
    """Imperal action: get_incident."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get_record("incident", params.sys_id)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_GET_INCIDENT_FAILED", retryable=exc.retryable)
    if not item:
        return ActionResult.error("Incident not found.", code="SNOW_INCIDENT_NOT_FOUND")
    return ActionResult.success(data=_record_to_incident(item), summary="Incident retrieved.")


@chat.function("create_incident", "Create a new incident.", action_type="write", chain_callable=True, data_model=Incident, event="servicenow-connector.create_incident", effects=["create:incident"])
async def create_incident(ctx, params: CreateIncidentParams) -> ActionResult:
    """Imperal action: create_incident."""
    fields = {
        "short_description": params.short_description, "description": params.description,
        "urgency": params.urgency, "impact": params.impact,
    }
    if params.category:
        fields["category"] = params.category
    if params.caller_id:
        fields["caller_id"] = params.caller_id
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_record("incident", fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_CREATE_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_incident(item), summary=f"Incident {item.get('number', '')} created.")


@chat.function("update_incident", "Update selected fields of an existing incident (state, priority, assignment, notes). Only given fields change.", action_type="write", chain_callable=True, data_model=Incident, event="servicenow-connector.update_incident", effects=["update:incident"])
async def update_incident(ctx, params: UpdateIncidentParams) -> ActionResult:
    """Imperal action: update_incident."""
    fields: dict = {}
    if params.state:
        fields["state"] = params.state
    if params.priority:
        fields["priority"] = params.priority
    if params.assigned_to:
        fields["assigned_to"] = params.assigned_to
    if params.work_notes:
        fields["work_notes"] = params.work_notes
    if params.close_notes:
        fields["close_notes"] = params.close_notes
    if not fields:
        return ActionResult.error("No fields supplied to update.", code="SNOW_NO_FIELDS")
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_record("incident", params.sys_id, fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_UPDATE_INCIDENT_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_incident(item), summary="Incident updated.")


def _record_to_problem(item: dict) -> Problem:
    return Problem(sys_id=str(item.get("sys_id", "")), title=item.get("number", ""), number=item.get("number", ""), short_description=item.get("short_description", ""), state=str(item.get("state", "")), raw=item)


def _record_to_change(item: dict) -> ChangeRequest:
    return ChangeRequest(sys_id=str(item.get("sys_id", "")), title=item.get("number", ""), number=item.get("number", ""), short_description=item.get("short_description", ""), state=str(item.get("state", "")), type=item.get("type", ""), approval=item.get("approval", ""), raw=item)


def _record_to_request(item: dict) -> ServiceCatalogRequest:
    return ServiceCatalogRequest(sys_id=str(item.get("sys_id", "")), title=item.get("number", ""), number=item.get("number", ""), short_description=item.get("short_description", ""), state=str(item.get("state", "")), raw=item)


def _record_to_article(item: dict) -> KnowledgeArticle:
    return KnowledgeArticle(sys_id=str(item.get("sys_id", "")), title=item.get("number", ""), number=item.get("number", ""), short_description=item.get("short_description", ""), raw=item)


def _record_to_ci(item: dict) -> CmdbCI:
    return CmdbCI(sys_id=str(item.get("sys_id", "")), title=item.get("name", ""), name=item.get("name", ""), ci_class=item.get("sys_class_name", ""), raw=item)


@chat.function("list_problems", "List problems in the connected ServiceNow instance, optionally filtered by state.", action_type="read", chain_callable=True, data_model=ProblemList, event="servicenow-connector.list_problems")
async def list_problems(ctx, params: ListProblemsParams) -> ActionResult:
    """Imperal action: list_problems."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        query = f"state={params.state}" if params.state else ""
        items = await client.list_table("problem", query=query, limit=params.limit)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_LIST_PROBLEMS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ProblemList(problems=[_record_to_problem(i) for i in items]), summary="Problems listed.")


@chat.function("create_problem", "Create a new problem record.", action_type="write", chain_callable=True, data_model=Problem, event="servicenow-connector.create_problem", effects=["create:problem"])
async def create_problem(ctx, params: CreateProblemParams) -> ActionResult:
    """Imperal action: create_problem."""
    fields = {"short_description": params.short_description, "description": params.description}
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_record("problem", fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_CREATE_PROBLEM_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_problem(item), summary=f"Problem {item.get('number', '')} created.")


@chat.function("update_problem", "Update selected fields of an existing problem. Only given fields change.", action_type="write", chain_callable=True, data_model=Problem, event="servicenow-connector.update_problem", effects=["update:problem"])
async def update_problem(ctx, params: UpdateProblemParams) -> ActionResult:
    """Imperal action: update_problem."""
    fields: dict = {}
    if params.state:
        fields["state"] = params.state
    if params.work_notes:
        fields["work_notes"] = params.work_notes
    if not fields:
        return ActionResult.error("No fields supplied to update.", code="SNOW_NO_FIELDS")
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_record("problem", params.sys_id, fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_UPDATE_PROBLEM_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_problem(item), summary="Problem updated.")


@chat.function("list_change_requests", "List change requests in the connected ServiceNow instance, optionally filtered by state.", action_type="read", chain_callable=True, data_model=ChangeRequestList, event="servicenow-connector.list_change_requests")
async def list_change_requests(ctx, params: ListChangeParams) -> ActionResult:
    """Imperal action: list_change_requests."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        clauses = []
        if params.state:
            clauses.append(f"state={params.state}")
        if params.approval:
            clauses.append(f"approval={params.approval}")
        items = await client.list_table("change_request", query="^".join(clauses), limit=params.limit)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_LIST_CHANGES_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ChangeRequestList(changes=[_record_to_change(i) for i in items]), summary="Change requests listed.")


@chat.function("create_change_request", "Create a new change request.", action_type="write", chain_callable=True, data_model=ChangeRequest, event="servicenow-connector.create_change_request", effects=["create:change_request"])
async def create_change_request(ctx, params: CreateChangeParams) -> ActionResult:
    """Imperal action: create_change_request."""
    fields = {"short_description": params.short_description, "description": params.description, "type": params.type}
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_record("change_request", fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_CREATE_CHANGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_change(item), summary=f"Change request {item.get('number', '')} created.")


@chat.function("update_change_request", "Update selected fields of an existing change request (state, approval). Only given fields change.", action_type="write", chain_callable=True, data_model=ChangeRequest, event="servicenow-connector.update_change_request", effects=["update:change_request"])
async def update_change_request(ctx, params: UpdateChangeParams) -> ActionResult:
    """Imperal action: update_change_request."""
    fields: dict = {}
    if params.state:
        fields["state"] = params.state
    if params.approval:
        fields["approval"] = params.approval
    if params.work_notes:
        fields["work_notes"] = params.work_notes
    if not fields:
        return ActionResult.error("No fields supplied to update.", code="SNOW_NO_FIELDS")
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_record("change_request", params.sys_id, fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_UPDATE_CHANGE_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_change(item), summary="Change request updated.")


@chat.function("list_requests", "List Service Catalog requests in the connected ServiceNow instance, optionally filtered by state.", action_type="read", chain_callable=True, data_model=ServiceCatalogRequestList, event="servicenow-connector.list_requests")
async def list_requests(ctx, params: ListRequestsParams) -> ActionResult:
    """Imperal action: list_requests."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        query = f"state={params.state}" if params.state else ""
        items = await client.list_table("sc_request", query=query, limit=params.limit)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_LIST_REQUESTS_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ServiceCatalogRequestList(requests=[_record_to_request(i) for i in items]), summary="Requests listed.")


@chat.function("create_request", "Create a new Service Catalog request.", action_type="write", chain_callable=True, data_model=ServiceCatalogRequest, event="servicenow-connector.create_request", effects=["create:sc_request"])
async def create_request(ctx, params: CreateRequestParams) -> ActionResult:
    """Imperal action: create_request."""
    fields = {"short_description": params.short_description, "description": params.description}
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_record("sc_request", fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_CREATE_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_request(item), summary=f"Request {item.get('number', '')} created.")


@chat.function("update_request", "Update selected fields of an existing Service Catalog request. Only given fields change.", action_type="write", chain_callable=True, data_model=ServiceCatalogRequest, event="servicenow-connector.update_request", effects=["update:sc_request"])
async def update_request(ctx, params: UpdateRequestParams) -> ActionResult:
    """Imperal action: update_request."""
    fields: dict = {}
    if params.state:
        fields["state"] = params.state
    if params.work_notes:
        fields["work_notes"] = params.work_notes
    if not fields:
        return ActionResult.error("No fields supplied to update.", code="SNOW_NO_FIELDS")
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_record("sc_request", params.sys_id, fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_UPDATE_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=_record_to_request(item), summary="Request updated.")


@chat.function("list_knowledge_articles", "List Knowledge articles in the connected ServiceNow instance.", action_type="read", chain_callable=True, data_model=KnowledgeArticleList, event="servicenow-connector.list_knowledge_articles")
async def list_knowledge_articles(ctx, params: ListKnowledgeParams) -> ActionResult:
    """Imperal action: list_knowledge_articles."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_table("kb_knowledge", limit=params.limit)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_LIST_KB_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=KnowledgeArticleList(articles=[_record_to_article(i) for i in items]), summary="Knowledge articles listed.")


@chat.function("list_cmdb_cis", "List Configuration Items (CIs) in the CMDB, optionally filtered by class.", action_type="read", chain_callable=True, data_model=CmdbCIList, event="servicenow-connector.list_cmdb_cis")
async def list_cmdb_cis(ctx, params: ListCmdbParams) -> ActionResult:
    """Imperal action: list_cmdb_cis."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        table = params.ci_class or "cmdb_ci"
        items = await client.list_table(table, limit=params.limit)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_LIST_CMDB_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=CmdbCIList(cis=[_record_to_ci(i) for i in items]), summary="Cmdb cis listed.")


@chat.function("list_table", "List records from any ServiceNow table by name -- a generic passthrough for tables not covered by typed wrappers (e.g. custom tables).", action_type="read", chain_callable=True, data_model=TableRecordList, event="servicenow-connector.list_table")
async def list_table(ctx, params: ListTableParams) -> ActionResult:
    """Imperal action: list_table."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        items = await client.list_table(params.table, query=params.query, limit=params.limit, offset=params.offset, fields=params.fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_LIST_TABLE_FAILED", retryable=exc.retryable)
    records = [TableRecord(sys_id=str(i.get("sys_id", "")), title=str(i.get("sys_id", "")), table=params.table, raw=i) for i in items]
    return ActionResult.success(data=TableRecordList(table=params.table, records=records), summary="Table listed.")


@chat.function("get_record", "Read one record from any ServiceNow table by sys_id.", action_type="read", chain_callable=True, data_model=TableRecord, event="servicenow-connector.get_record")
async def get_record(ctx, params: GetRecordParams) -> ActionResult:
    """Imperal action: get_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get_record(params.table, params.sys_id)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_GET_RECORD_FAILED", retryable=exc.retryable)
    if not item:
        return ActionResult.error("Record not found.", code="SNOW_RECORD_NOT_FOUND")
    return ActionResult.success(data=TableRecord(sys_id=str(item.get("sys_id", "")), title=str(item.get("sys_id", "")), table=params.table, raw=item), summary="Record retrieved.")


@chat.function("create_record", "Create a new record on any ServiceNow table -- a generic passthrough for tables not covered by typed wrappers.", action_type="write", chain_callable=True, data_model=TableRecord, event="servicenow-connector.create_record", effects=["create:resource"])
async def create_record(ctx, params: CreateRecordParams) -> ActionResult:
    """Imperal action: create_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.create_record(params.table, params.fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_CREATE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=TableRecord(sys_id=str(item.get("sys_id", "")), title=str(item.get("sys_id", "")), table=params.table, raw=item), summary="Record created.")


@chat.function("update_record", "Update selected fields of an existing record on any ServiceNow table. Only given fields change.", action_type="write", chain_callable=True, data_model=TableRecord, event="servicenow-connector.update_record", effects=["update:resource"])
async def update_record(ctx, params: UpdateRecordParams) -> ActionResult:
    """Imperal action: update_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.update_record(params.table, params.sys_id, params.fields)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_UPDATE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=TableRecord(sys_id=str(item.get("sys_id", "")), title=str(item.get("sys_id", "")), table=params.table, raw=item), summary="Record updated.")


@chat.function("delete_record", "Permanently delete a record from any ServiceNow table by sys_id. Cannot be undone.", action_type="write", chain_callable=True, data_model=DeleteResult, event="servicenow-connector.delete_record", effects=["delete:resource"])
async def delete_record(ctx, params: DeleteRecordParams) -> ActionResult:
    """Imperal action: delete_record."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.delete_record(params.table, params.sys_id)
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_DELETE_RECORD_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=DeleteResult(id=params.sys_id, title=params.table, deleted=True), summary="Record deleted.")


@chat.function("audit_instance_health", "Build one aggregated health snapshot for the connected ServiceNow instance: open incidents, critical incidents, open problems, pending changes, open requests.", action_type="read", chain_callable=True, data_model=HealthAudit, event="servicenow-connector.audit_instance_health")
async def audit_instance_health(ctx, params: ConnectionRefParams) -> ActionResult:
    """Imperal action: audit_instance_health."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        open_incidents = await client.list_table("incident", query="active=true", limit=1)
        open_incidents_count = len(await client.list_table("incident", query="active=true", limit=1000, fields="sys_id"))
        critical = len(await client.list_table("incident", query="active=true^priority=1", limit=1000, fields="sys_id"))
        open_problems = len(await client.list_table("problem", query="active=true", limit=1000, fields="sys_id"))
        pending_changes = len(await client.list_table("change_request", query="state!=3^state!=4", limit=1000, fields="sys_id"))
        open_requests = len(await client.list_table("sc_request", query="active=true", limit=1000, fields="sys_id"))
    except sc.ServiceNowError as exc:
        return ActionResult.error(str(exc), code="SNOW_AUDIT_FAILED", retryable=exc.retryable)
    summary = f"{open_incidents_count} open incidents ({critical} critical), {open_problems} open problems, {pending_changes} pending changes, {open_requests} open requests."
    return ActionResult.success(data=HealthAudit(open_incidents=open_incidents_count, critical_incidents=critical, open_problems=open_problems, pending_changes=pending_changes, open_requests=open_requests, summary=summary), summary="Instance health audit ready.")
