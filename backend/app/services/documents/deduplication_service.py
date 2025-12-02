"""
Email and document deduplication service.
Handles thread consolidation, duplicate detection, and content hashing.
"""
from typing import Optional, List, Dict, Any, Set, Tuple
from collections import defaultdict
import hashlib
import re
from datetime import datetime

from loguru import logger


class DeduplicationService:
    """
    Service for detecting and handling duplicate emails and documents.
    Critical for reducing the 150+ email-related requests per quarter workload.
    """

    def __init__(self):
        self.content_hashes: Set[str] = set()
        self.conversation_groups: Dict[str, List[Dict]] = defaultdict(list)

    def compute_content_hash(
        self,
        content: str,
        normalize: bool = True,
    ) -> str:
        """
        Compute hash of content for deduplication.

        Args:
            content: Text content to hash
            normalize: Whether to normalize whitespace and case

        Returns:
            SHA-256 hash string
        """
        if normalize:
            # Normalize whitespace and convert to lowercase
            content = re.sub(r'\s+', ' ', content.strip().lower())

        return hashlib.sha256(content.encode()).hexdigest()

    def compute_email_signature(self, email: Dict[str, Any]) -> str:
        """
        Compute a unique signature for an email based on key fields.
        More robust than content hash for email deduplication.

        Args:
            email: Email record with subject, sender, recipients, date, body_preview

        Returns:
            SHA-256 hash signature
        """
        # Normalize email components
        subject = email.get("subject", "").strip().lower()
        sender = email.get("sender_email", "").strip().lower()
        sent_date = email.get("sent_date", "")
        if isinstance(sent_date, datetime):
            sent_date = sent_date.isoformat()

        # Use body preview for content comparison (faster than full body)
        body_preview = email.get("body_preview", "").strip()[:500].lower()

        # Create signature
        signature_content = f"{subject}|{sender}|{sent_date}|{body_preview}"
        return hashlib.sha256(signature_content.encode()).hexdigest()

    def is_duplicate_email(
        self,
        email: Dict[str, Any],
        existing_hashes: Set[str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an email is a duplicate of an existing one.

        Args:
            email: Email to check
            existing_hashes: Set of existing email hashes

        Returns:
            Tuple of (is_duplicate, matching_hash)
        """
        signature = self.compute_email_signature(email)

        if signature in existing_hashes:
            return True, signature

        return False, signature

    def deduplicate_emails(
        self,
        emails: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Deduplicate a list of emails.

        Args:
            emails: List of email records

        Returns:
            Dictionary with unique emails and duplicate info
        """
        seen_hashes: Dict[str, Dict] = {}
        unique_emails = []
        duplicates = []

        for email in emails:
            signature = self.compute_email_signature(email)

            if signature in seen_hashes:
                # Mark as duplicate
                duplicates.append({
                    "email": email,
                    "duplicate_of": seen_hashes[signature].get("message_id"),
                    "signature": signature,
                })
            else:
                seen_hashes[signature] = email
                unique_emails.append(email)

        logger.info(
            f"Deduplicated emails: {len(emails)} -> {len(unique_emails)} "
            f"({len(duplicates)} duplicates removed)"
        )

        return {
            "unique_emails": unique_emails,
            "duplicates": duplicates,
            "stats": {
                "total_input": len(emails),
                "unique_count": len(unique_emails),
                "duplicate_count": len(duplicates),
                "reduction_percent": round(
                    (len(duplicates) / len(emails) * 100) if emails else 0, 1
                ),
            },
        }

    def group_email_threads(
        self,
        emails: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group emails into conversation threads.

        Args:
            emails: List of email records with conversation_id

        Returns:
            Dictionary mapping conversation_id to list of emails
        """
        threads: Dict[str, List[Dict]] = defaultdict(list)

        for email in emails:
            conversation_id = email.get("conversation_id")
            if conversation_id:
                threads[conversation_id].append(email)
            else:
                # Create pseudo-thread for standalone emails
                email_id = email.get("message_id", email.get("id", "unknown"))
                threads[f"standalone_{email_id}"].append(email)

        # Sort each thread by date
        for thread_id in threads:
            threads[thread_id].sort(
                key=lambda x: x.get("sent_date", "") or x.get("received_date", "")
            )

        return dict(threads)

    def consolidate_thread(
        self,
        thread_emails: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Consolidate an email thread for efficient review.
        Returns the most complete representation of the thread.

        Args:
            thread_emails: List of emails in a thread (sorted by date)

        Returns:
            Consolidated thread information
        """
        if not thread_emails:
            return {}

        # Get unique participants
        participants = set()
        for email in thread_emails:
            participants.add(email.get("sender_email", "").lower())
            for recipient in email.get("recipient_to", []):
                participants.add(recipient.lower())
            for recipient in email.get("recipient_cc", []):
                participants.add(recipient.lower())

        participants.discard("")

        # Get the root email (first in thread)
        root_email = thread_emails[0]

        # Get the most recent email (last in thread)
        latest_email = thread_emails[-1]

        # Count attachments
        total_attachments = sum(
            email.get("attachment_count", 0) or (1 if email.get("has_attachments") else 0)
            for email in thread_emails
        )

        return {
            "conversation_id": root_email.get("conversation_id"),
            "thread_subject": root_email.get("subject", "No Subject"),
            "email_count": len(thread_emails),
            "unique_participants": list(participants),
            "participant_count": len(participants),
            "first_email_date": root_email.get("sent_date") or root_email.get("received_date"),
            "last_email_date": latest_email.get("sent_date") or latest_email.get("received_date"),
            "total_attachments": total_attachments,
            "root_email_id": root_email.get("message_id"),
            "latest_email_id": latest_email.get("message_id"),
            "emails": thread_emails,
        }

    def analyze_thread_for_review(
        self,
        thread: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze a consolidated thread to determine review strategy.
        For long threads, recommend reviewing only the final email.

        Args:
            thread: Consolidated thread from consolidate_thread()

        Returns:
            Analysis with review recommendations
        """
        email_count = thread.get("email_count", 0)
        emails = thread.get("emails", [])

        # Determine review strategy
        if email_count == 1:
            strategy = "review_single"
            review_emails = emails
        elif email_count <= 3:
            strategy = "review_all"
            review_emails = emails
        else:
            # For long threads, the final email typically contains the full thread
            strategy = "review_final"
            review_emails = [emails[-1]] if emails else []

        return {
            **thread,
            "review_strategy": strategy,
            "review_email_count": len(review_emails),
            "review_emails": review_emails,
            "time_saved_estimate": max(0, email_count - len(review_emails)),
        }

    def process_emails_for_pia(
        self,
        emails: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Complete email processing pipeline for PIA requests:
        1. Deduplicate emails
        2. Group into threads
        3. Consolidate threads
        4. Generate review recommendations

        Args:
            emails: List of raw email records

        Returns:
            Processed email data ready for review
        """
        # Step 1: Deduplicate
        dedup_result = self.deduplicate_emails(emails)
        unique_emails = dedup_result["unique_emails"]

        # Step 2: Group into threads
        threads = self.group_email_threads(unique_emails)

        # Step 3: Consolidate and analyze each thread
        processed_threads = []
        total_review_emails = 0
        total_time_saved = 0

        for thread_id, thread_emails in threads.items():
            consolidated = self.consolidate_thread(thread_emails)
            analyzed = self.analyze_thread_for_review(consolidated)
            processed_threads.append(analyzed)

            total_review_emails += analyzed.get("review_email_count", 0)
            total_time_saved += analyzed.get("time_saved_estimate", 0)

        # Sort threads by date (most recent first)
        processed_threads.sort(
            key=lambda x: x.get("last_email_date", ""),
            reverse=True
        )

        return {
            "threads": processed_threads,
            "thread_count": len(processed_threads),
            "deduplication_stats": dedup_result["stats"],
            "processing_stats": {
                "original_email_count": len(emails),
                "unique_email_count": len(unique_emails),
                "thread_count": len(processed_threads),
                "review_email_count": total_review_emails,
                "emails_saved_from_review": total_time_saved,
                "efficiency_gain_percent": round(
                    (total_time_saved / len(emails) * 100) if emails else 0, 1
                ),
            },
        }

    def compute_document_hash(self, content: bytes) -> str:
        """
        Compute hash for binary document content.

        Args:
            content: Document content bytes

        Returns:
            SHA-256 hash string
        """
        return hashlib.sha256(content).hexdigest()

    def deduplicate_documents(
        self,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Deduplicate documents based on content hash.

        Args:
            documents: List of document records with 'file_hash' or 'content'

        Returns:
            Dictionary with unique documents and duplicate info
        """
        seen_hashes: Dict[str, Dict] = {}
        unique_documents = []
        duplicates = []

        for doc in documents:
            # Get or compute hash
            file_hash = doc.get("file_hash")
            if not file_hash and doc.get("content"):
                file_hash = self.compute_document_hash(doc["content"])

            if not file_hash:
                # Can't deduplicate without hash
                unique_documents.append(doc)
                continue

            if file_hash in seen_hashes:
                duplicates.append({
                    "document": doc,
                    "duplicate_of": seen_hashes[file_hash].get("id"),
                    "file_hash": file_hash,
                })
            else:
                seen_hashes[file_hash] = doc
                unique_documents.append(doc)

        return {
            "unique_documents": unique_documents,
            "duplicates": duplicates,
            "stats": {
                "total_input": len(documents),
                "unique_count": len(unique_documents),
                "duplicate_count": len(duplicates),
            },
        }


# Singleton instance
_dedup_service: Optional[DeduplicationService] = None


def get_deduplication_service() -> DeduplicationService:
    """Get or create the deduplication service singleton."""
    global _dedup_service
    if _dedup_service is None:
        _dedup_service = DeduplicationService()
    return _dedup_service
