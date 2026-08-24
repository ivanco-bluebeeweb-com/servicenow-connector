"""Thin ServiceNow Table API REST client.

Supports both OAuth2 (client credentials) and Basic Auth, since ServiceNow
tenants commonly use either depending on how their Application Registry /
integration user is configured.
"""
from __future__ import annotations

import base64
import time
from typing import Any

import httpx


class ServiceNowError(RuntimeError):
    """A safe provider-facing error; never includes credentials."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ServiceNowClient:
    """REST client for the Now Platform Table API."""

    def __init__(
        self,
        instance_host: str,
        auth_mode: str = "basic",
        username: str = "",
        password: str = "",
        client_id: str = "",
        client_secret: str = "",
        *,
        timeout: float = 30.0,
    ):
        host = (instance_host or "").strip()
        host = host.replace("https://", "").replace("http://", "").rstrip("/")
        if not host:
            raise ServiceNowError("Instance host is required, e.g. 'acme.service-now.com'.")
        self.base_url = f"https://{host}"
        self.auth_mode = auth_mode
        self.username = username or ""
        self.password = password or ""
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""
        self.timeout = timeout
        self._token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_oauth_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry - 30:
            return self._token
        token_url = f"{self.base_url}/oauth_token.do"
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            try:
                resp = await http_client.post(token_url, data=data)
            except httpx.RequestError as exc:
                raise ServiceNowError(f"Could not reach ServiceNow instance: {exc}", retryable=True) from exc
        if resp.status_code != 200:
            raise ServiceNowError(f"ServiceNow OAuth token request failed ({resp.status_code}).", retryable=resp.status_code >= 500)
        payload = resp.json()
        self._token = payload.get("access_token", "")
        self._token_expiry = now + int(payload.get("expires_in", 1800))
        if not self._token:
            raise ServiceNowError("ServiceNow did not return an access token.")
        return self._token

    async def _headers(self) -> dict:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.auth_mode == "oauth2":
            token = await self._get_oauth_token()
            headers["Authorization"] = f"Bearer {token}"
        else:
            creds = f"{self.username}:{self.password}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(creds).decode('ascii')}"
        return headers

    async def request(self, method: str, path: str, *, params: dict | None = None, json_body: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            try:
                resp = await http_client.request(method, url, headers=headers, params=params, json=json_body)
            except httpx.RequestError as exc:
                raise ServiceNowError(f"Could not reach ServiceNow instance: {exc}", retryable=True) from exc
        if resp.status_code == 401:
            raise ServiceNowError("ServiceNow rejected the credentials (401). Check the instance host, auth mode, and account permissions.")
        if resp.status_code == 403:
            raise ServiceNowError("ServiceNow denied access to this resource (403). The account may lack the required role (e.g. itil).")
        if resp.status_code == 404:
            raise ServiceNowError("ServiceNow table or record not found (404). Check the table name and sys_id.")
        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = (body.get("error") or {}).get("message", "") if isinstance(body, dict) else ""
            except Exception:
                detail = ""
            raise ServiceNowError(f"ServiceNow request failed ({resp.status_code}): {detail}", retryable=resp.status_code >= 500)
        if not resp.content:
            return {}
        try:
            return resp.json()
        except Exception as exc:
            raise ServiceNowError(f"ServiceNow returned a non-JSON response: {exc}") from exc

    async def ping(self) -> None:
        await self.list_table("sys_user", limit=1)

    async def list_table(self, table: str, *, query: str = "", limit: int = 50, offset: int = 0, fields: str = "") -> list[dict]:
        params: dict[str, Any] = {"sysparm_limit": limit, "sysparm_offset": offset}
        if query:
            params["sysparm_query"] = query
        if fields:
            params["sysparm_fields"] = fields
        body = await self.request("GET", f"/api/now/table/{table}", params=params)
        return body.get("result", []) or []

    async def get_record(self, table: str, sys_id: str) -> dict:
        body = await self.request("GET", f"/api/now/table/{table}/{sys_id}")
        return body.get("result", {}) or {}

    async def create_record(self, table: str, fields: dict) -> dict:
        body = await self.request("POST", f"/api/now/table/{table}", json_body=fields)
        return body.get("result", {}) or {}

    async def update_record(self, table: str, sys_id: str, fields: dict) -> dict:
        body = await self.request("PATCH", f"/api/now/table/{table}/{sys_id}", json_body=fields)
        return body.get("result", {}) or {}

    async def delete_record(self, table: str, sys_id: str) -> None:
        await self.request("DELETE", f"/api/now/table/{table}/{sys_id}")

    async def aggregate(self, table: str, *, group_by: str = "", query: str = "") -> list[dict]:
        params: dict[str, Any] = {"sysparm_count": "true"}
        if group_by:
            params["sysparm_group_by"] = group_by
        if query:
            params["sysparm_query"] = query
        body = await self.request("GET", f"/api/now/stats/{table}", params=params)
        return body.get("result", {}).get("stats", []) if isinstance(body.get("result"), dict) else []
