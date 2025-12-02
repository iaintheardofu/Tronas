"""
Microsoft SharePoint document retrieval service.
Retrieves documents from SharePoint sites and libraries for PIA request processing.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import hashlib
import asyncio
from pathlib import Path

from loguru import logger

from app.services.microsoft.graph_client import MSGraphClient, get_graph_client


class SharePointService:
    """
    Service for retrieving and processing documents from SharePoint Online.
    Supports site discovery, library browsing, and document search.
    """

    def __init__(self, graph_client: Optional[MSGraphClient] = None):
        self.graph = graph_client or get_graph_client()

    async def get_sites(self) -> List[Dict[str, Any]]:
        """
        Get all SharePoint sites accessible to the application.

        Returns:
            List of SharePoint sites
        """
        return await self.graph.get_paginated("/sites?search=*")

    async def get_site_by_path(self, site_path: str) -> Dict[str, Any]:
        """
        Get a specific SharePoint site by its path.

        Args:
            site_path: Site path (e.g., "contoso.sharepoint.com:/sites/team")

        Returns:
            Site information
        """
        return await self.graph.get(f"/sites/{site_path}")

    async def get_site_lists(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Get all document libraries and lists in a site.

        Args:
            site_id: SharePoint site ID

        Returns:
            List of lists/libraries
        """
        return await self.graph.get_paginated(f"/sites/{site_id}/lists")

    async def get_document_libraries(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Get only document libraries from a site (excluding other list types).

        Args:
            site_id: SharePoint site ID

        Returns:
            List of document libraries
        """
        lists = await self.get_site_lists(site_id)
        return [
            lst for lst in lists
            if lst.get("list", {}).get("template") == "documentLibrary"
        ]

    async def get_drive(self, site_id: str, drive_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a drive (document library) from a site.

        Args:
            site_id: SharePoint site ID
            drive_id: Specific drive ID (default: root drive)

        Returns:
            Drive information
        """
        if drive_id:
            return await self.graph.get(f"/sites/{site_id}/drives/{drive_id}")
        return await self.graph.get(f"/sites/{site_id}/drive")

    async def get_drives(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Get all drives (document libraries) in a site.

        Args:
            site_id: SharePoint site ID

        Returns:
            List of drives
        """
        return await self.graph.get_paginated(f"/sites/{site_id}/drives")

    async def list_folder_contents(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str = "/",
    ) -> List[Dict[str, Any]]:
        """
        List contents of a folder in a document library.

        Args:
            site_id: SharePoint site ID
            drive_id: Drive ID
            folder_path: Folder path (default: root)

        Returns:
            List of items in the folder
        """
        if folder_path == "/" or not folder_path:
            endpoint = f"/sites/{site_id}/drives/{drive_id}/root/children"
        else:
            # URL encode the path
            encoded_path = folder_path.lstrip("/")
            endpoint = f"/sites/{site_id}/drives/{drive_id}/root:/{encoded_path}:/children"

        return await self.graph.get_paginated(endpoint)

    async def search_documents(
        self,
        query: str,
        site_ids: Optional[List[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        file_types: Optional[List[str]] = None,
        max_results: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Search for documents across SharePoint.

        Args:
            query: Search query
            site_ids: Limit search to specific sites
            date_from: Filter by creation/modification date
            date_to: Filter by creation/modification date
            file_types: Filter by file extensions
            max_results: Maximum results to return

        Returns:
            List of matching documents
        """
        # Build KQL query
        kql_parts = [query] if query else []

        if date_from:
            kql_parts.append(f"LastModifiedTime>={date_from.isoformat()}")
        if date_to:
            kql_parts.append(f"LastModifiedTime<={date_to.isoformat()}")
        if file_types:
            type_filter = " OR ".join([f'FileType="{ft}"' for ft in file_types])
            kql_parts.append(f"({type_filter})")

        search_query = " AND ".join(kql_parts) if kql_parts else "*"

        # Use Microsoft Search API
        request_body = {
            "requests": [
                {
                    "entityTypes": ["driveItem"],
                    "query": {"queryString": search_query},
                    "size": min(max_results, 500),
                }
            ]
        }

        try:
            result = await self.graph.post("/search/query", json_data=request_body)

            # Extract hits from search results
            hits = []
            for response in result.get("value", []):
                for hit_container in response.get("hitsContainers", []):
                    for hit in hit_container.get("hits", []):
                        hits.append(hit.get("resource", {}))

            logger.info(f"Search returned {len(hits)} documents")
            return hits

        except Exception as e:
            logger.error(f"SharePoint search failed: {e}")
            raise

    async def get_document_metadata(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed metadata for a document.

        Args:
            site_id: SharePoint site ID
            drive_id: Drive ID
            item_id: Item ID

        Returns:
            Document metadata
        """
        return await self.graph.get(
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}"
        )

    async def download_document(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
    ) -> bytes:
        """
        Download a document's content.

        Args:
            site_id: SharePoint site ID
            drive_id: Drive ID
            item_id: Item ID

        Returns:
            Document content as bytes
        """
        # Get download URL
        item = await self.graph.get(
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}"
        )

        download_url = item.get("@microsoft.graph.downloadUrl")
        if not download_url:
            raise ValueError("No download URL available for this item")

        # Download content directly (doesn't need Graph auth)
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url)
            response.raise_for_status()
            return response.content

    async def get_document_versions(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a document.

        Args:
            site_id: SharePoint site ID
            drive_id: Drive ID
            item_id: Item ID

        Returns:
            List of document versions
        """
        return await self.graph.get_paginated(
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/versions"
        )

    async def crawl_library(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str = "/",
        recursive: bool = True,
        file_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Crawl a document library and return all documents.

        Args:
            site_id: SharePoint site ID
            drive_id: Drive ID
            folder_path: Starting folder path
            recursive: Include subfolders
            file_filter: Filter by file extensions

        Returns:
            List of all documents found
        """
        all_documents = []

        async def crawl_folder(path: str):
            items = await self.list_folder_contents(site_id, drive_id, path)

            for item in items:
                if item.get("folder"):
                    # It's a folder
                    if recursive:
                        subfolder_path = f"{path.rstrip('/')}/{item['name']}"
                        await crawl_folder(subfolder_path)
                elif item.get("file"):
                    # It's a file
                    if file_filter:
                        ext = Path(item.get("name", "")).suffix.lower().lstrip(".")
                        if ext not in file_filter:
                            continue

                    all_documents.append({
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "path": f"{path.rstrip('/')}/{item['name']}",
                        "size": item.get("size", 0),
                        "mime_type": item.get("file", {}).get("mimeType"),
                        "created": item.get("createdDateTime"),
                        "modified": item.get("lastModifiedDateTime"),
                        "created_by": item.get("createdBy", {}).get("user", {}).get("email"),
                        "modified_by": item.get("lastModifiedBy", {}).get("user", {}).get("email"),
                        "web_url": item.get("webUrl"),
                        "site_id": site_id,
                        "drive_id": drive_id,
                    })

                # Yield control periodically
                await asyncio.sleep(0)

        await crawl_folder(folder_path)
        logger.info(f"Crawled {len(all_documents)} documents from {site_id}/{drive_id}")
        return all_documents

    async def search_multiple_sites(
        self,
        site_ids: List[str],
        query: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        max_results_per_site: int = 200,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search documents across multiple SharePoint sites.

        Args:
            site_ids: List of site IDs to search
            query: Search query
            date_from: Filter by date
            date_to: Filter by date
            max_results_per_site: Max results per site

        Returns:
            Dictionary mapping site ID to list of documents
        """
        results = {}

        async def search_site(site_id: str):
            try:
                # Get all drives in the site
                drives = await self.get_drives(site_id)
                site_docs = []

                for drive in drives:
                    docs = await self.crawl_library(
                        site_id=site_id,
                        drive_id=drive["id"],
                    )
                    # Filter by query if provided
                    if query:
                        query_lower = query.lower()
                        docs = [
                            d for d in docs
                            if query_lower in d.get("name", "").lower()
                        ]
                    site_docs.extend(docs[:max_results_per_site])

                return site_id, site_docs[:max_results_per_site]

            except Exception as e:
                logger.error(f"Failed to search site {site_id}: {e}")
                return site_id, []

        # Process sites concurrently with rate limiting
        tasks = [search_site(sid) for sid in site_ids]
        batch_size = 3

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            for site_id, docs in batch_results:
                results[site_id] = docs
            if i + batch_size < len(tasks):
                await asyncio.sleep(1)

        return results

    def compute_document_hash(self, content: bytes) -> str:
        """
        Compute SHA-256 hash of document content for deduplication.

        Args:
            content: Document content bytes

        Returns:
            SHA-256 hash string
        """
        return hashlib.sha256(content).hexdigest()


# Singleton instance
_sharepoint_service: Optional[SharePointService] = None


def get_sharepoint_service() -> SharePointService:
    """Get or create the SharePoint service singleton."""
    global _sharepoint_service
    if _sharepoint_service is None:
        _sharepoint_service = SharePointService()
    return _sharepoint_service
