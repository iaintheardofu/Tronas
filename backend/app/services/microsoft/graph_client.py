"""
Microsoft Graph API client for Azure AD authentication and API access.
Handles authentication via MSAL and provides base client for Graph API operations.
"""
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timedelta

import httpx
from msal import ConfidentialClientApplication
from loguru import logger

from app.core.config import settings


class MSGraphClient:
    """
    Microsoft Graph API client with MSAL authentication.
    Supports application-level permissions for accessing organizational data.
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    GRAPH_BETA_URL = "https://graph.microsoft.com/beta"

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._http_client: Optional[httpx.AsyncClient] = None

        # Initialize MSAL application
        if settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID:
            self._msal_app = ConfidentialClientApplication(
                client_id=settings.AZURE_CLIENT_ID,
                client_credential=settings.AZURE_CLIENT_SECRET,
                authority=f"{settings.AZURE_AUTHORITY}/{settings.AZURE_TENANT_ID}",
            )
        else:
            self._msal_app = None
            logger.warning("Azure AD credentials not configured")

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def _acquire_token(self) -> str:
        """
        Acquire access token using client credentials flow.
        Caches token until near expiration.
        """
        # Check if we have a valid cached token
        if (
            self._access_token
            and self._token_expires_at
            and datetime.utcnow() < self._token_expires_at - timedelta(minutes=5)
        ):
            return self._access_token

        if not self._msal_app:
            raise ValueError("Microsoft Graph client not configured")

        # Acquire new token
        result = self._msal_app.acquire_token_for_client(
            scopes=settings.MS_GRAPH_SCOPES
        )

        if "access_token" in result:
            self._access_token = result["access_token"]
            # Token typically valid for 1 hour
            self._token_expires_at = datetime.utcnow() + timedelta(
                seconds=result.get("expires_in", 3600)
            )
            logger.debug("Acquired new Microsoft Graph access token")
            return self._access_token
        else:
            error = result.get("error_description", result.get("error", "Unknown error"))
            logger.error(f"Failed to acquire token: {error}")
            raise ValueError(f"Failed to acquire Microsoft Graph token: {error}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        use_beta: bool = False,
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to Microsoft Graph API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON body data
            use_beta: Use beta API endpoint

        Returns:
            JSON response data
        """
        token = await self._acquire_token()
        client = await self._get_http_client()

        base_url = self.GRAPH_BETA_URL if use_beta else self.GRAPH_BASE_URL
        url = f"{base_url}{endpoint}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Graph API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Graph API request failed: {e}")
            raise

    async def get(
        self, endpoint: str, params: Optional[Dict] = None, use_beta: bool = False
    ) -> Dict[str, Any]:
        """Make GET request to Graph API."""
        return await self._make_request("GET", endpoint, params=params, use_beta=use_beta)

    async def post(
        self, endpoint: str, json_data: Optional[Dict] = None, use_beta: bool = False
    ) -> Dict[str, Any]:
        """Make POST request to Graph API."""
        return await self._make_request("POST", endpoint, json_data=json_data, use_beta=use_beta)

    async def patch(
        self, endpoint: str, json_data: Optional[Dict] = None, use_beta: bool = False
    ) -> Dict[str, Any]:
        """Make PATCH request to Graph API."""
        return await self._make_request("PATCH", endpoint, json_data=json_data, use_beta=use_beta)

    async def delete(self, endpoint: str, use_beta: bool = False) -> Dict[str, Any]:
        """Make DELETE request to Graph API."""
        return await self._make_request("DELETE", endpoint, use_beta=use_beta)

    async def get_paginated(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        max_pages: int = 100,
        use_beta: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all pages of a paginated Graph API response.

        Args:
            endpoint: API endpoint
            params: Query parameters
            max_pages: Maximum number of pages to retrieve
            use_beta: Use beta API endpoint

        Returns:
            Combined list of all items from all pages
        """
        all_items = []
        page_count = 0

        result = await self.get(endpoint, params=params, use_beta=use_beta)
        all_items.extend(result.get("value", []))
        page_count += 1

        # Follow @odata.nextLink for pagination
        while "@odata.nextLink" in result and page_count < max_pages:
            next_link = result["@odata.nextLink"]
            # Extract endpoint from full URL
            if self.GRAPH_BASE_URL in next_link:
                next_endpoint = next_link.replace(self.GRAPH_BASE_URL, "")
            elif self.GRAPH_BETA_URL in next_link:
                next_endpoint = next_link.replace(self.GRAPH_BETA_URL, "")
            else:
                break

            result = await self.get(next_endpoint, use_beta=use_beta)
            all_items.extend(result.get("value", []))
            page_count += 1

            # Yield control to prevent blocking
            await asyncio.sleep(0)

        logger.debug(f"Retrieved {len(all_items)} items from {page_count} pages")
        return all_items

    # Convenience methods for common operations

    async def get_users(self, select: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get all users in the organization."""
        params = {}
        if select:
            params["$select"] = ",".join(select)
        return await self.get_paginated("/users", params=params)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get a specific user by ID or UPN."""
        return await self.get(f"/users/{user_id}")

    async def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups in the organization."""
        return await self.get_paginated("/groups")

    async def get_sites(self) -> List[Dict[str, Any]]:
        """Get all SharePoint sites."""
        return await self.get_paginated("/sites?search=*")

    async def search(
        self,
        query: str,
        entity_types: List[str],
        size: int = 25,
    ) -> Dict[str, Any]:
        """
        Search across Microsoft 365 content.

        Args:
            query: Search query string
            entity_types: Types to search (driveItem, message, site, etc.)
            size: Number of results per entity type

        Returns:
            Search results
        """
        request_body = {
            "requests": [
                {
                    "entityTypes": entity_types,
                    "query": {"queryString": query},
                    "size": size,
                }
            ]
        }
        return await self.post("/search/query", json_data=request_body)


# Singleton instance
_graph_client: Optional[MSGraphClient] = None


def get_graph_client() -> MSGraphClient:
    """Get or create the Graph client singleton."""
    global _graph_client
    if _graph_client is None:
        _graph_client = MSGraphClient()
    return _graph_client
