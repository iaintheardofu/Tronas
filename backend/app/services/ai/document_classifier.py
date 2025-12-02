"""
Document classification service for Texas PIA requests.
Classifies documents according to Texas Government Code Chapter 552 exemptions.
"""
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import json
import asyncio

from openai import AsyncOpenAI
from loguru import logger

from app.core.config import settings


class PIAClassification(str, Enum):
    """Texas PIA classification categories based on Chapter 552 exemptions."""
    RESPONSIVE = "responsive"
    NON_RESPONSIVE = "non_responsive"
    ATTORNEY_CLIENT_PRIVILEGE = "attorney_client_privilege"
    LEGISLATIVE_PRIVILEGE = "legislative_privilege"
    LAW_ENFORCEMENT = "law_enforcement"
    MEDICAL_INFORMATION = "medical_information"
    PERSONNEL_RECORDS = "personnel_records"
    TRADE_SECRETS = "trade_secrets"
    DELIBERATIVE_PROCESS = "deliberative_process"
    PENDING_LITIGATION = "pending_litigation"
    PERSONAL_INFORMATION = "personal_information"
    NEEDS_REVIEW = "needs_review"


# Texas Government Code Chapter 552 exemption descriptions
EXEMPTION_DESCRIPTIONS = {
    PIAClassification.ATTORNEY_CLIENT_PRIVILEGE: {
        "section": "552.107",
        "description": "Information that attorney-client privilege protects",
        "indicators": [
            "Legal advice between attorney and client",
            "Attorney work product",
            "Litigation strategy documents",
            "Legal opinions and analysis"
        ]
    },
    PIAClassification.LEGISLATIVE_PRIVILEGE: {
        "section": "552.008",
        "description": "Correspondence and communications between legislative offices",
        "indicators": [
            "Communications with state legislators",
            "Legislative correspondence",
            "Policy discussions with elected officials"
        ]
    },
    PIAClassification.LAW_ENFORCEMENT: {
        "section": "552.108",
        "description": "Information related to law enforcement investigations",
        "indicators": [
            "Ongoing investigation details",
            "Confidential informant information",
            "Investigative techniques and procedures",
            "Criminal intelligence information"
        ]
    },
    PIAClassification.MEDICAL_INFORMATION: {
        "section": "552.101 (HIPAA)",
        "description": "Protected health information under HIPAA",
        "indicators": [
            "Patient records",
            "Medical diagnoses",
            "Treatment information",
            "Health insurance details"
        ]
    },
    PIAClassification.PERSONNEL_RECORDS: {
        "section": "552.102",
        "description": "Personnel information including evaluations",
        "indicators": [
            "Employee performance reviews",
            "Disciplinary records",
            "Personnel complaints",
            "Internal investigations of employees"
        ]
    },
    PIAClassification.TRADE_SECRETS: {
        "section": "552.110",
        "description": "Trade secrets and proprietary business information",
        "indicators": [
            "Proprietary formulas or processes",
            "Competitive business information",
            "Confidential financial data",
            "Technical specifications submitted confidentially"
        ]
    },
    PIAClassification.DELIBERATIVE_PROCESS: {
        "section": "552.111",
        "description": "Inter-agency or intra-agency memoranda not yet final",
        "indicators": [
            "Draft policy documents",
            "Internal recommendations",
            "Pre-decisional discussions",
            "Staff recommendations before final decision"
        ]
    },
    PIAClassification.PENDING_LITIGATION: {
        "section": "552.103",
        "description": "Information related to pending litigation",
        "indicators": [
            "Documents related to active lawsuits",
            "Settlement negotiations",
            "Litigation hold materials"
        ]
    },
    PIAClassification.PERSONAL_INFORMATION: {
        "section": "552.101, 552.102",
        "description": "Personal identifying information",
        "indicators": [
            "Social Security numbers",
            "Driver's license numbers",
            "Personal financial information",
            "Home addresses and personal phone numbers"
        ]
    }
}

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert legal analyst specializing in Texas Public Information Act (PIA) requests under Texas Government Code Chapter 552.

Your task is to classify documents according to Texas PIA exemptions and determine:
1. Whether the document is responsive to the specific request
2. If responsive, what exemptions (if any) may apply
3. What portions may need redaction

IMPORTANT CONTEXT:
- The Texas PIA requires disclosure of public information unless a specific exemption applies
- When in doubt, err on the side of disclosure (Texas has a strong presumption of openness)
- Multiple exemptions may apply to a single document
- Partial redaction is often appropriate rather than withholding entire documents

EXEMPTION CATEGORIES:
1. Attorney-Client Privilege (552.107) - Legal advice and attorney work product
2. Legislative Privilege (552.008) - Communications with legislators
3. Law Enforcement (552.108) - Investigation records
4. Medical Information (552.101/HIPAA) - Protected health information
5. Personnel Records (552.102) - Employee evaluations, complaints
6. Trade Secrets (552.110) - Proprietary business information
7. Deliberative Process (552.111) - Pre-decisional internal discussions
8. Pending Litigation (552.103) - Active lawsuit materials
9. Personal Information (552.101, 552.102) - SSN, DL, personal financial

Respond ONLY with valid JSON matching this exact schema:
{
    "classification": "responsive|non_responsive|needs_review",
    "confidence": 0.0-1.0,
    "exemptions": [
        {
            "category": "exemption_type",
            "section": "552.XXX",
            "confidence": 0.0-1.0,
            "reasoning": "explanation"
        }
    ],
    "redaction_needed": true|false,
    "redaction_areas": ["description of what should be redacted"],
    "reasoning": "overall explanation of classification decision",
    "key_indicators": ["list of key phrases or content that led to this classification"]
}"""


class DocumentClassifier:
    """
    Document classifier for Texas PIA requests.
    Analyzes documents and classifies according to Chapter 552 exemptions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.CLASSIFICATION_MODEL

        if settings.AZURE_OPENAI_ENDPOINT:
            # Use Azure OpenAI
            from openai import AsyncAzureOpenAI
            self.client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version="2024-02-15-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )
            self.model = settings.AZURE_OPENAI_DEPLOYMENT
        else:
            # Use standard OpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def classify_document(
        self,
        text_content: str,
        request_description: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        max_text_length: int = 15000,
    ) -> Dict[str, Any]:
        """
        Classify a single document for PIA responsiveness and exemptions.

        Args:
            text_content: Extracted text content of the document
            request_description: Description of what the PIA request is seeking
            document_metadata: Optional metadata (filename, author, dates)
            max_text_length: Maximum text length to send to model

        Returns:
            Classification result with exemptions and confidence scores
        """
        # Truncate text if too long
        if len(text_content) > max_text_length:
            text_content = text_content[:max_text_length] + "\n[TRUNCATED]"

        # Build context with metadata
        metadata_context = ""
        if document_metadata:
            metadata_context = f"""
Document Metadata:
- Filename: {document_metadata.get('filename', 'Unknown')}
- Author: {document_metadata.get('author', 'Unknown')}
- Created: {document_metadata.get('created_date', 'Unknown')}
- Modified: {document_metadata.get('modified_date', 'Unknown')}
- Type: {document_metadata.get('document_type', 'Unknown')}
"""

        user_prompt = f"""PIA REQUEST DESCRIPTION:
{request_description}

{metadata_context}

DOCUMENT CONTENT:
{text_content}

Analyze this document and provide your classification in the required JSON format."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # Validate and normalize result
            result = self._normalize_classification_result(result)

            logger.debug(f"Classified document: {result.get('classification')} ({result.get('confidence')})")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification response: {e}")
            return self._create_error_result("Failed to parse AI response")
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return self._create_error_result(str(e))

    async def classify_email(
        self,
        subject: str,
        body: str,
        sender: str,
        recipients: List[str],
        request_description: str,
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Classify an email message for PIA responsiveness and exemptions.

        Args:
            subject: Email subject line
            body: Email body text
            sender: Sender email address
            recipients: List of recipient addresses
            request_description: PIA request description
            attachments: Optional list of attachment names

        Returns:
            Classification result
        """
        email_content = f"""EMAIL:
From: {sender}
To: {', '.join(recipients)}
Subject: {subject}

{body}
"""
        if attachments:
            email_content += f"\nAttachments: {', '.join(attachments)}"

        metadata = {
            "document_type": "email",
            "author": sender,
            "filename": f"Email: {subject[:50]}",
        }

        return await self.classify_document(
            text_content=email_content,
            request_description=request_description,
            document_metadata=metadata,
        )

    async def classify_batch(
        self,
        documents: List[Dict[str, Any]],
        request_description: str,
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple documents concurrently.

        Args:
            documents: List of documents with 'text' and optional 'metadata'
            request_description: PIA request description
            concurrency: Number of concurrent classifications

        Returns:
            List of classification results
        """
        semaphore = asyncio.Semaphore(concurrency)
        results = []

        async def classify_with_limit(doc: Dict[str, Any], index: int):
            async with semaphore:
                result = await self.classify_document(
                    text_content=doc.get("text", ""),
                    request_description=request_description,
                    document_metadata=doc.get("metadata"),
                )
                result["document_index"] = index
                result["document_id"] = doc.get("id")
                return result

        tasks = [
            classify_with_limit(doc, i)
            for i, doc in enumerate(documents)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(self._create_error_result(str(result)))
            else:
                processed_results.append(result)

        return processed_results

    def _normalize_classification_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate classification result."""
        # Ensure required fields exist
        normalized = {
            "classification": result.get("classification", "needs_review"),
            "confidence": min(max(result.get("confidence", 0.5), 0.0), 1.0),
            "exemptions": result.get("exemptions", []),
            "redaction_needed": result.get("redaction_needed", False),
            "redaction_areas": result.get("redaction_areas", []),
            "reasoning": result.get("reasoning", ""),
            "key_indicators": result.get("key_indicators", []),
        }

        # Validate classification value
        valid_classifications = ["responsive", "non_responsive", "needs_review"]
        if normalized["classification"] not in valid_classifications:
            normalized["classification"] = "needs_review"

        # Normalize exemptions
        for exemption in normalized["exemptions"]:
            exemption["confidence"] = min(max(exemption.get("confidence", 0.5), 0.0), 1.0)

        return normalized

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create an error result for failed classifications."""
        return {
            "classification": "needs_review",
            "confidence": 0.0,
            "exemptions": [],
            "redaction_needed": False,
            "redaction_areas": [],
            "reasoning": f"Classification failed: {error_message}",
            "key_indicators": [],
            "error": error_message,
        }

    def get_exemption_description(self, category: str) -> Dict[str, Any]:
        """Get detailed description of a Texas PIA exemption category."""
        try:
            enum_value = PIAClassification(category)
            return EXEMPTION_DESCRIPTIONS.get(enum_value, {})
        except ValueError:
            return {}


class ClassificationSummary:
    """Helper class for aggregating classification results."""

    def __init__(self):
        self.total = 0
        self.responsive = 0
        self.non_responsive = 0
        self.needs_review = 0
        self.by_exemption: Dict[str, int] = {}
        self.redaction_needed = 0
        self.avg_confidence = 0.0
        self._confidence_sum = 0.0

    def add_result(self, result: Dict[str, Any]):
        """Add a classification result to the summary."""
        self.total += 1

        classification = result.get("classification", "needs_review")
        if classification == "responsive":
            self.responsive += 1
        elif classification == "non_responsive":
            self.non_responsive += 1
        else:
            self.needs_review += 1

        for exemption in result.get("exemptions", []):
            category = exemption.get("category", "unknown")
            self.by_exemption[category] = self.by_exemption.get(category, 0) + 1

        if result.get("redaction_needed"):
            self.redaction_needed += 1

        self._confidence_sum += result.get("confidence", 0.5)
        self.avg_confidence = self._confidence_sum / self.total

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "total_documents": self.total,
            "responsive": self.responsive,
            "non_responsive": self.non_responsive,
            "needs_review": self.needs_review,
            "exemptions_breakdown": self.by_exemption,
            "redaction_needed": self.redaction_needed,
            "average_confidence": round(self.avg_confidence, 3),
            "responsiveness_rate": round(self.responsive / self.total, 3) if self.total > 0 else 0,
        }


# Singleton instance
_classifier: Optional[DocumentClassifier] = None


def get_document_classifier() -> DocumentClassifier:
    """Get or create the document classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = DocumentClassifier()
    return _classifier
