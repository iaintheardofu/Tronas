"""
Microsoft Outlook/Exchange email retrieval service.
Retrieves emails from user mailboxes for PIA request processing.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import hashlib
import asyncio

from loguru import logger

from app.services.microsoft.graph_client import MSGraphClient, get_graph_client


class OutlookService:
    """
    Service for retrieving and processing emails from Microsoft 365 mailboxes.
    Supports search, filtering, and bulk retrieval for PIA requests.
    """

    def __init__(self, graph_client: Optional[MSGraphClient] = None):
        self.graph = graph_client or get_graph_client()

    async def search_mailbox(
        self,
        mailbox: str,
        query: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        folders: Optional[List[str]] = None,
        max_results: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Search a mailbox for emails matching the query.

        Args:
            mailbox: User email address or ID
            query: Search query (KQL syntax)
            date_from: Start date filter
            date_to: End date filter
            folders: List of folder IDs to search (default: all)
            max_results: Maximum number of results

        Returns:
            List of email messages
        """
        # Build filter string
        filters = []

        if date_from:
            filters.append(f"receivedDateTime ge {date_from.isoformat()}T00:00:00Z")
        if date_to:
            filters.append(f"receivedDateTime le {date_to.isoformat()}T23:59:59Z")

        params = {
            "$select": (
                "id,subject,from,toRecipients,ccRecipients,bccRecipients,"
                "receivedDateTime,sentDateTime,bodyPreview,body,hasAttachments,"
                "conversationId,internetMessageId,importance,categories,"
                "isRead,isDraft,parentFolderId"
            ),
            "$top": min(max_results, 100),  # Max per page
            "$orderby": "receivedDateTime desc",
        }

        if query:
            params["$search"] = f'"{query}"'

        if filters:
            params["$filter"] = " and ".join(filters)

        endpoint = f"/users/{mailbox}/messages"

        try:
            messages = await self.graph.get_paginated(
                endpoint,
                params=params,
                max_pages=max_results // 100 + 1,
            )
            logger.info(f"Retrieved {len(messages)} emails from {mailbox}")
            return messages[:max_results]

        except Exception as e:
            logger.error(f"Failed to search mailbox {mailbox}: {e}")
            raise

    async def get_message(
        self,
        mailbox: str,
        message_id: str,
        include_body: bool = True,
    ) -> Dict[str, Any]:
        """
        Get a specific email message by ID.

        Args:
            mailbox: User email address or ID
            message_id: Message ID
            include_body: Include full body content

        Returns:
            Email message data
        """
        select_fields = [
            "id", "subject", "from", "toRecipients", "ccRecipients", "bccRecipients",
            "receivedDateTime", "sentDateTime", "hasAttachments", "conversationId",
            "internetMessageId", "importance", "categories", "isRead", "isDraft",
            "parentFolderId", "bodyPreview"
        ]

        if include_body:
            select_fields.append("body")

        params = {"$select": ",".join(select_fields)}

        return await self.graph.get(
            f"/users/{mailbox}/messages/{message_id}",
            params=params
        )

    async def get_message_attachments(
        self,
        mailbox: str,
        message_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get attachments for an email message.

        Args:
            mailbox: User email address or ID
            message_id: Message ID

        Returns:
            List of attachment metadata
        """
        endpoint = f"/users/{mailbox}/messages/{message_id}/attachments"
        return await self.graph.get_paginated(endpoint)

    async def download_attachment(
        self,
        mailbox: str,
        message_id: str,
        attachment_id: str,
    ) -> Dict[str, Any]:
        """
        Download a specific attachment.

        Args:
            mailbox: User email address or ID
            message_id: Message ID
            attachment_id: Attachment ID

        Returns:
            Attachment data including content bytes
        """
        endpoint = f"/users/{mailbox}/messages/{message_id}/attachments/{attachment_id}"
        return await self.graph.get(endpoint)

    async def get_conversation_thread(
        self,
        mailbox: str,
        conversation_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all messages in a conversation thread.

        Args:
            mailbox: User email address or ID
            conversation_id: Conversation ID

        Returns:
            List of messages in the thread, ordered by date
        """
        params = {
            "$filter": f"conversationId eq '{conversation_id}'",
            "$orderby": "receivedDateTime asc",
            "$select": (
                "id,subject,from,toRecipients,ccRecipients,"
                "receivedDateTime,sentDateTime,bodyPreview,body,"
                "hasAttachments,internetMessageId"
            ),
        }

        messages = await self.graph.get_paginated(
            f"/users/{mailbox}/messages",
            params=params
        )
        return messages

    async def get_mailbox_folders(self, mailbox: str) -> List[Dict[str, Any]]:
        """
        Get all folders in a mailbox.

        Args:
            mailbox: User email address or ID

        Returns:
            List of mail folders
        """
        return await self.graph.get_paginated(f"/users/{mailbox}/mailFolders")

    async def search_multiple_mailboxes(
        self,
        mailboxes: List[str],
        query: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        max_results_per_mailbox: int = 500,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search multiple mailboxes concurrently.

        Args:
            mailboxes: List of user email addresses
            query: Search query
            date_from: Start date filter
            date_to: End date filter
            max_results_per_mailbox: Max results per mailbox

        Returns:
            Dictionary mapping mailbox to list of messages
        """
        results = {}

        # Create search tasks for all mailboxes
        async def search_single(mailbox: str):
            try:
                messages = await self.search_mailbox(
                    mailbox=mailbox,
                    query=query,
                    date_from=date_from,
                    date_to=date_to,
                    max_results=max_results_per_mailbox,
                )
                return mailbox, messages
            except Exception as e:
                logger.error(f"Failed to search mailbox {mailbox}: {e}")
                return mailbox, []

        # Run searches concurrently with rate limiting
        tasks = [search_single(mb) for mb in mailboxes]

        # Process in batches to avoid rate limiting
        batch_size = 5
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            for mailbox, messages in batch_results:
                results[mailbox] = messages
            # Brief delay between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(0.5)

        total_messages = sum(len(msgs) for msgs in results.values())
        logger.info(f"Retrieved {total_messages} total emails from {len(mailboxes)} mailboxes")
        return results

    def compute_email_hash(self, message: Dict[str, Any]) -> str:
        """
        Compute a hash for email deduplication.
        Uses subject, sender, date, and body preview.

        Args:
            message: Email message data

        Returns:
            SHA-256 hash string
        """
        # Normalize key fields for hashing
        subject = message.get("subject", "").strip().lower()
        sender = message.get("from", {}).get("emailAddress", {}).get("address", "").lower()
        sent_date = message.get("sentDateTime", "")
        body_preview = message.get("bodyPreview", "").strip()[:500]

        hash_content = f"{subject}|{sender}|{sent_date}|{body_preview}"
        return hashlib.sha256(hash_content.encode()).hexdigest()

    def extract_email_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized metadata from a Graph API message.

        Args:
            message: Raw message from Graph API

        Returns:
            Standardized email metadata
        """
        from_addr = message.get("from", {}).get("emailAddress", {})
        to_addrs = [
            r.get("emailAddress", {}).get("address", "")
            for r in message.get("toRecipients", [])
        ]
        cc_addrs = [
            r.get("emailAddress", {}).get("address", "")
            for r in message.get("ccRecipients", [])
        ]
        bcc_addrs = [
            r.get("emailAddress", {}).get("address", "")
            for r in message.get("bccRecipients", [])
        ]

        return {
            "message_id": message.get("id"),
            "internet_message_id": message.get("internetMessageId"),
            "conversation_id": message.get("conversationId"),
            "subject": message.get("subject", ""),
            "sender_email": from_addr.get("address", ""),
            "sender_name": from_addr.get("name", ""),
            "recipient_to": to_addrs,
            "recipient_cc": cc_addrs,
            "recipient_bcc": bcc_addrs,
            "sent_date": message.get("sentDateTime"),
            "received_date": message.get("receivedDateTime"),
            "body_preview": message.get("bodyPreview", ""),
            "body_text": message.get("body", {}).get("content", "") if message.get("body", {}).get("contentType") == "text" else "",
            "body_html": message.get("body", {}).get("content", "") if message.get("body", {}).get("contentType") == "html" else "",
            "has_attachments": message.get("hasAttachments", False),
            "importance": message.get("importance"),
            "categories": message.get("categories", []),
            "is_read": message.get("isRead", True),
            "is_draft": message.get("isDraft", False),
            "folder_id": message.get("parentFolderId"),
            "content_hash": self.compute_email_hash(message),
        }


# Singleton instance
_outlook_service: Optional[OutlookService] = None


def get_outlook_service() -> OutlookService:
    """Get or create the Outlook service singleton."""
    global _outlook_service
    if _outlook_service is None:
        _outlook_service = OutlookService()
    return _outlook_service
