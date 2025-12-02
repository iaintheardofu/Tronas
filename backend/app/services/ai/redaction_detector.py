"""
Redaction detection and preparation service.
Identifies sensitive information that requires redaction under Texas PIA.
"""
from typing import Optional, List, Dict, Any
import re
import json

from openai import AsyncOpenAI
from loguru import logger

from app.core.config import settings


# Common PII patterns for regex-based detection
PII_PATTERNS = {
    "ssn": {
        "pattern": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        "description": "Social Security Number",
        "exemption": "552.101",
    },
    "drivers_license": {
        "pattern": r"\b[A-Z]{0,2}\d{5,12}\b",
        "description": "Driver's License Number (generic)",
        "exemption": "552.101",
    },
    "credit_card": {
        "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "description": "Credit Card Number",
        "exemption": "552.101",
    },
    "phone": {
        "pattern": r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "description": "Phone Number (may need contextual review)",
        "exemption": "552.102",
    },
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "description": "Email Address (may need contextual review)",
        "exemption": "552.102",
    },
    "date_of_birth": {
        "pattern": r"\b(?:DOB|Date of Birth|Born)[\s:]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "description": "Date of Birth",
        "exemption": "552.101",
    },
    "bank_account": {
        "pattern": r"\b(?:Account|Acct)[\s#:]*\d{8,17}\b",
        "description": "Bank Account Number",
        "exemption": "552.101",
    },
    "routing_number": {
        "pattern": r"\b(?:Routing|ABA)[\s#:]*\d{9}\b",
        "description": "Bank Routing Number",
        "exemption": "552.101",
    },
}

REDACTION_SYSTEM_PROMPT = """You are an expert at identifying sensitive information that requires redaction under the Texas Public Information Act (Chapter 552).

Your task is to analyze text and identify ALL portions that should be redacted, including:

1. **Personal Identifying Information (552.101)**
   - Social Security numbers
   - Driver's license numbers
   - Financial account numbers
   - Personal addresses and phone numbers (non-business)
   - Dates of birth
   - Medical record numbers

2. **Personnel Information (552.102)**
   - Employee home addresses
   - Personal phone numbers
   - Employee social security numbers
   - Information that would constitute a clearly unwarranted invasion of privacy

3. **Attorney-Client Privileged (552.107)**
   - Legal advice passages
   - Attorney work product
   - Litigation strategy discussions

4. **Medical/HIPAA Information**
   - Patient names in medical context
   - Diagnoses and treatments
   - Health conditions
   - Medical record numbers

5. **Law Enforcement Sensitive (552.108)**
   - Confidential informant identities
   - Investigative techniques
   - Victim information in certain contexts

For each identified item, provide:
- The exact text to redact
- The character position (start and end)
- The exemption category
- The confidence level

Respond ONLY with valid JSON:
{
    "redactions": [
        {
            "text": "exact text to redact",
            "start_pos": 0,
            "end_pos": 10,
            "category": "personal_information|medical|attorney_client|law_enforcement|other",
            "exemption_code": "552.XXX",
            "confidence": 0.0-1.0,
            "reason": "brief explanation"
        }
    ],
    "summary": {
        "total_redactions": 0,
        "categories": {"category_name": count},
        "high_confidence": 0,
        "needs_review": 0
    }
}"""


class RedactionDetector:
    """
    Detect and prepare redaction areas in documents.
    Uses both regex patterns and AI analysis for comprehensive detection.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.CLASSIFICATION_MODEL

        if settings.AZURE_OPENAI_ENDPOINT:
            from openai import AsyncAzureOpenAI
            self.client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version="2024-02-15-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )
            self.model = settings.AZURE_OPENAI_DEPLOYMENT
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

    def detect_pii_patterns(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII using regex patterns.

        Args:
            text: Text to scan for PII

        Returns:
            List of detected PII with positions
        """
        detections = []

        for pii_type, config in PII_PATTERNS.items():
            pattern = config["pattern"]
            for match in re.finditer(pattern, text, re.IGNORECASE):
                detections.append({
                    "text": match.group(),
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                    "category": "personal_information",
                    "pii_type": pii_type,
                    "exemption_code": config["exemption"],
                    "confidence": 0.9,  # High confidence for regex matches
                    "reason": config["description"],
                    "detection_method": "regex",
                })

        return detections

    async def detect_ai_redactions(
        self,
        text: str,
        context: Optional[str] = None,
        max_text_length: int = 10000,
    ) -> Dict[str, Any]:
        """
        Use AI to detect redaction areas that require more context understanding.

        Args:
            text: Text to analyze
            context: Optional context about the document
            max_text_length: Maximum text length to send

        Returns:
            AI detection results
        """
        # Truncate if needed
        if len(text) > max_text_length:
            text = text[:max_text_length] + "\n[TRUNCATED]"

        user_prompt = f"""Analyze the following text and identify ALL sensitive information that should be redacted under Texas PIA.

{f"CONTEXT: {context}" if context else ""}

TEXT TO ANALYZE:
{text}

Identify all redaction areas with their exact positions."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": REDACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Add detection method tag
            for redaction in result.get("redactions", []):
                redaction["detection_method"] = "ai"

            return result

        except Exception as e:
            logger.error(f"AI redaction detection failed: {e}")
            return {
                "redactions": [],
                "summary": {"error": str(e)},
            }

    async def detect_all_redactions(
        self,
        text: str,
        context: Optional[str] = None,
        use_ai: bool = True,
    ) -> Dict[str, Any]:
        """
        Comprehensive redaction detection using both regex and AI.

        Args:
            text: Text to analyze
            context: Optional context
            use_ai: Whether to use AI analysis

        Returns:
            Combined redaction detection results
        """
        # Start with regex-based detection
        regex_detections = self.detect_pii_patterns(text)

        if use_ai:
            # Add AI-based detection
            ai_result = await self.detect_ai_redactions(text, context)
            ai_detections = ai_result.get("redactions", [])
        else:
            ai_detections = []

        # Merge and deduplicate
        all_redactions = self._merge_redactions(regex_detections, ai_detections)

        # Generate summary
        summary = self._generate_summary(all_redactions)

        return {
            "redactions": all_redactions,
            "summary": summary,
            "text_length": len(text),
        }

    def _merge_redactions(
        self,
        regex_detections: List[Dict],
        ai_detections: List[Dict],
    ) -> List[Dict[str, Any]]:
        """
        Merge regex and AI detections, removing duplicates.
        """
        all_detections = []
        seen_ranges = set()

        # Add regex detections first (higher confidence)
        for detection in regex_detections:
            range_key = (detection["start_pos"], detection["end_pos"])
            if range_key not in seen_ranges:
                seen_ranges.add(range_key)
                all_detections.append(detection)

        # Add AI detections that don't overlap
        for detection in ai_detections:
            start = detection.get("start_pos", 0)
            end = detection.get("end_pos", 0)

            # Check for overlap with existing detections
            is_overlap = False
            for existing_start, existing_end in seen_ranges:
                if (start <= existing_end and end >= existing_start):
                    is_overlap = True
                    break

            if not is_overlap:
                seen_ranges.add((start, end))
                all_detections.append(detection)

        # Sort by position
        all_detections.sort(key=lambda x: x.get("start_pos", 0))

        return all_detections

    def _generate_summary(self, redactions: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics for redactions."""
        categories = {}
        high_confidence = 0
        needs_review = 0

        for redaction in redactions:
            category = redaction.get("category", "other")
            categories[category] = categories.get(category, 0) + 1

            confidence = redaction.get("confidence", 0.5)
            if confidence >= 0.8:
                high_confidence += 1
            elif confidence < 0.6:
                needs_review += 1

        return {
            "total_redactions": len(redactions),
            "categories": categories,
            "high_confidence": high_confidence,
            "needs_review": needs_review,
        }

    def apply_redactions(
        self,
        text: str,
        redactions: List[Dict[str, Any]],
        replacement: str = "[REDACTED]",
    ) -> str:
        """
        Apply redactions to text, replacing sensitive content.

        Args:
            text: Original text
            redactions: List of redaction areas
            replacement: Replacement string

        Returns:
            Redacted text
        """
        # Sort redactions by position in reverse order
        sorted_redactions = sorted(
            redactions,
            key=lambda x: x.get("start_pos", 0),
            reverse=True
        )

        result = text
        for redaction in sorted_redactions:
            start = redaction.get("start_pos")
            end = redaction.get("end_pos")
            if start is not None and end is not None:
                result = result[:start] + replacement + result[end:]

        return result

    def generate_redaction_report(
        self,
        redactions: List[Dict[str, Any]],
        document_name: str = "Document",
    ) -> str:
        """
        Generate a human-readable redaction report.

        Args:
            redactions: List of redactions
            document_name: Name of the document

        Returns:
            Formatted report string
        """
        report_lines = [
            f"REDACTION REPORT: {document_name}",
            "=" * 50,
            f"Total Redactions: {len(redactions)}",
            "",
            "REDACTION DETAILS:",
            "-" * 50,
        ]

        for i, redaction in enumerate(redactions, 1):
            report_lines.extend([
                f"\n{i}. {redaction.get('category', 'Unknown').upper()}",
                f"   Text: \"{redaction.get('text', 'N/A')[:50]}{'...' if len(redaction.get('text', '')) > 50 else ''}\"",
                f"   Exemption: {redaction.get('exemption_code', 'N/A')}",
                f"   Confidence: {redaction.get('confidence', 0):.0%}",
                f"   Reason: {redaction.get('reason', 'N/A')}",
                f"   Position: chars {redaction.get('start_pos', 'N/A')}-{redaction.get('end_pos', 'N/A')}",
            ])

        report_lines.extend([
            "",
            "=" * 50,
            "END OF REPORT",
        ])

        return "\n".join(report_lines)


# Singleton instance
_detector: Optional[RedactionDetector] = None


def get_redaction_detector() -> RedactionDetector:
    """Get or create the redaction detector singleton."""
    global _detector
    if _detector is None:
        _detector = RedactionDetector()
    return _detector
