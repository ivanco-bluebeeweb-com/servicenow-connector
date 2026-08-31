"""Pydantic input contracts and SDL result entities for ServiceNow Connector."""
from __future__ import annotations

from imperal_sdk import sdl
from pydantic import BaseModel, Field


class NoParams(BaseModel):
    pass


class ConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="Optional saved ServiceNow instance connection ID. Omit to use the first connected instance.")


class ConnectServiceNowParams(BaseModel):
    label: str = Field("", description="Friendly instance label, e.g. 'Acme Production'.")
    instance_host: str = Field(..., description="Instance hostname, e.g. 'acme.service-now.com'.")
    auth_mode: str = Field("basic", description="Authentication mode: 'basic' or 'oauth2'.")
    username: str = Field("", description="Integration user username (required for Basic Auth).")
    password: str = Field("", description="Integration user password (required for Basic Auth).")
    client_id: str = Field("", description="OAuth2 Application Registry client ID (required for OAuth2).")
    client_secret: str = Field("", description="OAuth2 Application Registry client secret (required for OAuth2).")


class DisconnectServiceNowParams(ConnectionRefParams):
    connection_id: str = Field(..., description="Saved ServiceNow instance connection ID to remove from Imperal.")


class ListTableParams(ConnectionRefParams):
    table: str = Field(..., description="Table name, e.g. 'incident', 'problem', 'change_request'.")
    query: str = Field("", description="Optional ServiceNow encoded query (sysparm_query), e.g. 'active=true^priority=1'.")
    limit: int = Field(50, description="Max records to return.")
    offset: int = Field(0, description="Pagination offset.")
    fields: str = Field("", description="Optional comma-separated field list to limit the response.")


class GetRecordParams(ConnectionRefParams):
    table: str = Field(..., description="Table name.")
    sys_id: str = Field(..., description="Record sys_id.")


class SysIdParams(ConnectionRefParams):
    sys_id: str = Field(..., description="Record sys_id.")


class CreateRecordParams(ConnectionRefParams):
    table: str = Field(..., description="Table name.")
    fields: dict = Field(..., description="Field name/value pairs to set on the new record.")


class UpdateRecordParams(ConnectionRefParams):
    table: str = Field(..., description="Table name.")
    sys_id: str = Field(..., description="Record sys_id.")
    fields: dict = Field(..., description="Field name/value pairs to update.")


class DeleteRecordParams(ConnectionRefParams):
    table: str = Field(..., description="Table name.")
    sys_id: str = Field(..., description="Record sys_id.")


class ListIncidentsParams(ConnectionRefParams):
    state: str = Field("", description="Optional incident state filter, e.g. '1' (New), '2' (In Progress), '6' (Resolved), '7' (Closed).")
    priority: str = Field("", description="Optional priority filter: '1' (Critical) through '5' (Planning).")
    assigned_to: str = Field("", description="Optional sys_id of the assigned user to filter by.")
    limit: int = Field(50, description="Max records to return.")


class CreateIncidentParams(ConnectionRefParams):
    short_description: str = Field(..., description="Short summary of the incident.")
    description: str = Field("", description="Full description of the incident.")
    urgency: str = Field("3", description="Urgency: '1' (High) to '3' (Low).")
    impact: str = Field("3", description="Impact: '1' (High) to '3' (Low).")
    category: str = Field("", description="Category, e.g. 'network', 'hardware', 'software'.")
    caller_id: str = Field("", description="sys_id of the caller/requester, if known.")


class UpdateIncidentParams(ConnectionRefParams):
    sys_id: str = Field(..., description="Incident sys_id.")
    state: str = Field("", description="New state, e.g. '2' (In Progress), '6' (Resolved), '7' (Closed).")
    work_notes: str = Field("", description="Work note to append (internal, not customer-visible).")
    close_notes: str = Field("", description="Close notes (required by ServiceNow when resolving/closing).")
    close_code: str = Field("", description="Close code, e.g. 'Solved (Permanently)'.")


class ListProblemsParams(ConnectionRefParams):
    state: str = Field("", description="Optional problem state filter.")
    limit: int = Field(50, description="Max records to return.")


class CreateProblemParams(ConnectionRefParams):
    short_description: str = Field(..., description="Short summary of the problem.")
    description: str = Field("", description="Full description of the problem.")


class UpdateProblemParams(ConnectionRefParams):
    sys_id: str = Field(..., description="Problem sys_id.")
    state: str = Field("", description="New state, e.g. '1' (Open), '3' (Closed/Resolved).")
    work_notes: str = Field("", description="Work note to append (internal, not customer-visible).")


class ListChangeParams(ConnectionRefParams):
    state: str = Field("", description="Optional change request state filter.")
    approval: str = Field("", description="Optional approval status filter: 'requested', 'approved', 'rejected'.")
    type: str = Field("", description="Optional change type filter: 'standard', 'normal', 'emergency'.")
    limit: int = Field(50, description="Max records to return.")


class CreateChangeParams(ConnectionRefParams):
    short_description: str = Field(..., description="Short summary of the change.")
    description: str = Field("", description="Full description of the change.")
    type: str = Field("normal", description="Change type: 'standard', 'normal', or 'emergency'.")


class UpdateChangeParams(ConnectionRefParams):
    sys_id: str = Field(..., description="Change request sys_id.")
    state: str = Field("", description="New state value.")
    approval: str = Field("", description="New approval status: 'approved' or 'rejected'.")
    work_notes: str = Field("", description="Work note to append (internal, not customer-visible).")


class ListRequestsParams(ConnectionRefParams):
    state: str = Field("", description="Optional request state filter.")
    limit: int = Field(50, description="Max records to return.")


class CreateRequestParams(ConnectionRefParams):
    short_description: str = Field(..., description="Short summary of the request.")
    description: str = Field("", description="Full description of the request.")


class UpdateRequestParams(ConnectionRefParams):
    sys_id: str = Field(..., description="Service Catalog request sys_id.")
    state: str = Field("", description="New state value.")
    work_notes: str = Field("", description="Work note to append (internal, not customer-visible).")


class ListKnowledgeParams(ConnectionRefParams):
    query: str = Field("", description="Optional free-text search against short_description.")
    limit: int = Field(50, description="Max records to return.")


class ListCmdbParams(ConnectionRefParams):
    ci_class: str = Field("", description="Optional CI class table name, e.g. 'cmdb_ci_server'. Defaults to base 'cmdb_ci'.")
    query: str = Field("", description="Optional encoded query filter.")
    limit: int = Field(50, description="Max records to return.")


class AddAttachmentParams(ConnectionRefParams):
    table: str = Field(..., description="Table name the record belongs to.")
    sys_id: str = Field(..., description="Record sys_id to attach the file to.")
    file_name: str = Field(..., description="File name, e.g. 'screenshot.png'.")
    content_base64: str = Field(..., description="Base64-encoded file content.")
    content_type: str = Field("application/octet-stream", description="MIME type of the file.")


class AuditHealthParams(ConnectionRefParams):
    pass


class BulkUpdateStateParams(ConnectionRefParams):
    table: str = Field(..., description="Table name.")
    sys_ids: list[str] = Field(..., description="List of record sys_ids to update.")
    state: str = Field(..., description="New state value to apply to every record.")


# ---- SDL entities ----

class ServiceNowConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    label: str
    instance_host: str
    auth_mode: str
    connected: bool = True


class ConnectionList(sdl.Entity):
    id: str = ""
    title: str = ""
    connections: list[ServiceNowConnection] = []


class DeleteResult(sdl.Entity):
    id: str = ""
    title: str = ""
    deleted: bool = False


class TableRecord(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    table: str
    raw: dict = {}


class TableRecordList(sdl.Entity):
    id: str = ""
    title: str = ""
    table: str
    records: list[TableRecord] = []


class Incident(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    number: str = ""
    short_description: str = ""
    state: str = ""
    priority: str = ""
    urgency: str = ""
    impact: str = ""
    assigned_to: str = ""
    raw: dict = {}


class IncidentList(sdl.Entity):
    id: str = ""
    title: str = ""
    incidents: list[Incident] = []


class Problem(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    number: str = ""
    short_description: str = ""
    state: str = ""
    raw: dict = {}


class ProblemList(sdl.Entity):
    id: str = ""
    title: str = ""
    problems: list[Problem] = []


class ChangeRequest(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    number: str = ""
    short_description: str = ""
    state: str = ""
    type: str = ""
    approval: str = ""
    raw: dict = {}


class ChangeRequestList(sdl.Entity):
    id: str = ""
    title: str = ""
    changes: list[ChangeRequest] = []


class ServiceCatalogRequest(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    number: str = ""
    short_description: str = ""
    state: str = ""
    raw: dict = {}


class ServiceCatalogRequestList(sdl.Entity):
    id: str = ""
    title: str = ""
    requests: list[ServiceCatalogRequest] = []


class KnowledgeArticle(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    number: str = ""
    short_description: str = ""
    raw: dict = {}


class KnowledgeArticleList(sdl.Entity):
    id: str = ""
    title: str = ""
    articles: list[KnowledgeArticle] = []


class CmdbCI(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    name: str = ""
    ci_class: str = ""
    raw: dict = {}


class CmdbCIList(sdl.Entity):
    id: str = ""
    title: str = ""
    cis: list[CmdbCI] = []


class Attachment(sdl.Entity):
    id: str = ""
    title: str = ""
    sys_id: str
    file_name: str = ""
    table: str = ""


class HealthAudit(sdl.Entity):
    id: str = ""
    title: str = ""
    open_incidents: int = 0
    critical_incidents: int = 0
    open_problems: int = 0
    pending_changes: int = 0
    open_requests: int = 0
    summary: str = ""


class BulkOutcome(sdl.Entity):
    id: str = ""
    title: str = ""
    updated: int = 0
    failed: int = 0
    errors: list[str] = []
