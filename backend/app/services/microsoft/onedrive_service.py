"""
Microsoft OneDrive document retrieval service.
Retrieves documents from OneDrive for Business for PIA request processing.
"""
from typing import Optional, List, Dict, Any
from datetime import date
import hashlib
import asyncio

from loguru import logger

from app.services.microsoft.graph_client import MSGraphClient, get_graph_client


class OneDriveService:
    """
    Service for retrieving and processing documents from OneDrive for Business.
    Supports user drive access, search, and bulk retrieval.
    """

    def __init__(self, graph_client: Optional[MSGraphClient] = None):
        self.graph = graph_client or get_graph_client()

    async def get_user_drive(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's OneDrive root drive.

        Args:
            user_id: User ID or email address

        Returns:
            Drive information
        """
        return await self.graph.get(f"/users/{user_id}/drive")

    async def list_root_contents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List contents of user's OneDrive root folder.

        Args:
            user_id: User ID or email address

        Returns:
            List of items in root folder
        """
        return await self.graph.get_paginated(
            f"/users/{user_id}/drive/root/children"
        )

    async def list_folder_contents(
        self,
        user_id: str,
        folder_path: str = "/",
    ) -> List[Dict[str, Any]]:
        """
        List contents of a specific folder in user's OneDrive.

        Args:
            user_id: User ID or email address
            folder_path: Folder path relative to root

        Returns:
            List of items in the folder
        """
        if folder_path == "/" or not folder_path:
            return await self.list_root_contents(user_id)

        encoded_path = folder_path.lstrip("/")
        return await self.graph.get_paginated(
            f"/users/{user_id}/drive/root:/{encoded_path}:/children"
        )

    async def search_drive(
        self,
        user_id: str,
        query: str,
        max_results: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Search a user's OneDrive for files matching query.

        Args:
            user_id: User ID or email address
            query: Search query string
            max_results: Maximum number of results

        Returns:
            List of matching items
        """
        endpoint = f"/users/{user_id}/drive/root/search(q='{query}')"
        items = await self.graph.get_paginated(endpoint)
        return items[:max_results]

    async def get_item(
        self,
        user_id: str,
        item_id: str,
    ) -> Dict[str, Any]:
        """
        Get metadata for a specific item.

        Args:
            user_id: User ID or email address
            item_id: Item ID

        Returns:
            Item metadata
        """
        return await self.graph.get(f"/users/{user_id}/drive/items/{item_id}")

    async def download_item(
        self,
        user_id: str,
        item_id: str,
    ) -> bytes:
        """
        Download a file's content.

        Args:
            user_id: User ID or email address
            item_id: Item ID

        Returns:
            File content as bytes
        """
        item = await self.get_item(user_id, item_id)
        download_url = item.get("@microsoft.graph.downloadUrl")

        if not download_url:
            raise ValueError("No download URL available for this item")

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(download_url)
            response.raise_for_status()
            return response.content

    async def crawl_user_drive(
        self,
        user_id: str,
        folder_path: str = "/",
        recursive: bool = True,
        file_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Crawl a user's OneDrive and return all documents.

        Args:
            user_id: User ID or email address
            folder_path: Starting folder path
            recursive: Include subfolders
            file_filter: Filter by file extensions

        Returns:
            List of all documents found
        """
        from pathlib import Path
        all_documents = []

        async def crawl_folder(path: str):
            items = await self.list_folder_contents(user_id, path)

            for item in items:
                if item.get("folder"):
                    if recursive:
                        subfolder_path = f"{path.rstrip('/')}/{item['name']}"
                        await crawl_folder(subfolder_path)
                elif item.get("file"):
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
                        "user_id": user_id,
                        "source": "onedrive",
                    })

                await asyncio.sleep(0)

        await crawl_folder(folder_path)
        logger.info(f"Crawled {len(all_documents)} documents from {user_id}'s OneDrive")
        return all_documents

    async def crawl_multiple_users(
        self,
        user_ids: List[str],
        query: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        max_docs_per_user: int = 500,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Crawl OneDrive for multiple users.

        Args:
            user_ids: List of user IDs or email addresses
            query: Optional search query to filter results
            date_from: Filter by modification date
            date_to: Filter by modification date
            max_docs_per_user: Maximum documents per user

        Returns:
            Dictionary mapping user ID to list of documents
        """
        results = {}

        async def process_user(user_id: str):
            try:
                if query:
                    docs = await self.search_drive(user_id, query, max_docs_per_user)
                else:
                    docs = await self.crawl_user_drive(user_id)

                # Apply date filtering if specified
                if date_from or date_to:
                    filtered_docs = []
                    for doc in docs:
                        modified = doc.get("modified")
                        if modified:
                            from datetime import datetime
                            mod_date = datetime.fromisoformat(modified.replace("Z", "+00:00")).date()
                            if date_from and mod_date < date_from:
                                continue
                            if date_to and mod_date > date_to:
                                continue
                        filtered_docs.append(doc)
                    docs = filtered_docs

                return user_id, docs[:max_docs_per_user]

            except Exception as e:
                logger.error(f"Failed to process OneDrive for {user_id}: {e}")
                return user_id, []

        # Process users in batches
        tasks = [process_user(uid) for uid in user_ids]
        batch_size = 5

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            for user_id, docs in batch_results:
                results[user_id] = docs
            if i + batch_size < len(tasks):
                await asyncio.sleep(1)

        total_docs = sum(len(docs) for docs in results.values())
        logger.info(f"Retrieved {total_docs} documents from {len(user_ids)} users' OneDrive")
        return results


# Singleton instance
_onedrive_service: Optional[OneDriveService] = None


def get_onedrive_service() -> OneDriveService:
    """Get or create the OneDrive service singleton."""
    global _onedrive_service
    if _onedrive_service is None:
        _onedrive_service = OneDriveService()
    return _onedrive_service
