"""
Azure Document Intelligence (Form Recognizer) OCR Service.
State-of-the-art document intelligence for the Tronas PIA system.
"""
import os
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile

from loguru import logger

# Azure Document Intelligence SDK
try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    logger.warning("Azure Form Recognizer SDK not installed. Install with: pip install azure-ai-formrecognizer")


class AzureDocumentIntelligenceOCR:
    """
    Azure Document Intelligence OCR Service.

    Provides state-of-the-art document analysis including:
    - High-accuracy OCR for scanned documents
    - Table extraction
    - Key-value pair extraction
    - Document structure analysis
    - Handwriting recognition
    - Multi-language support
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Azure Document Intelligence client.

        Args:
            endpoint: Azure Form Recognizer endpoint URL
            api_key: Azure Form Recognizer API key
        """
        self.endpoint = endpoint or os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_FORM_RECOGNIZER_KEY")

        self.client: Optional[DocumentAnalysisClient] = None
        self._initialized = False

        # Supported document types
        self.supported_extensions = {
            ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
            ".heif", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"
        }

        # Analysis models
        self.models = {
            "prebuilt-read": "General document reading and OCR",
            "prebuilt-document": "Document with key-value pairs and tables",
            "prebuilt-layout": "Document layout analysis",
            "prebuilt-invoice": "Invoice processing",
            "prebuilt-receipt": "Receipt processing",
            "prebuilt-idDocument": "ID document processing",
        }

    async def initialize(self) -> bool:
        """
        Initialize the Azure client.

        Returns:
            True if initialization successful
        """
        if not AZURE_SDK_AVAILABLE:
            logger.error("Azure Form Recognizer SDK not available")
            return False

        if not self.endpoint or not self.api_key:
            logger.error("Azure Form Recognizer endpoint or API key not configured")
            return False

        try:
            self.client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            self._initialized = True
            logger.info("Azure Document Intelligence client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Azure client: {e}")
            return False

    def is_supported(self, file_path: str) -> bool:
        """
        Check if file type is supported for OCR.

        Args:
            file_path: Path to the file

        Returns:
            True if supported
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    async def analyze_document(
        self,
        file_path: str,
        model_id: str = "prebuilt-read",
        pages: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a document using Azure Document Intelligence.

        Args:
            file_path: Path to the document
            model_id: Azure model to use (prebuilt-read, prebuilt-document, etc.)
            pages: Page range to analyze (e.g., "1-3,5")

        Returns:
            Analysis result with extracted text, tables, and metadata
        """
        if not self._initialized:
            if not await self.initialize():
                return {"error": "Azure client not initialized", "text": ""}

        if not self.is_supported(file_path):
            return {
                "error": f"Unsupported file type: {Path(file_path).suffix}",
                "text": ""
            }

        try:
            # Read file content
            with open(file_path, "rb") as f:
                document_content = f.read()

            # Calculate hash for caching
            content_hash = hashlib.sha256(document_content).hexdigest()

            logger.info(f"Analyzing document: {file_path} with model: {model_id}")

            # Start analysis
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                document=document_content,
                pages=pages,
            )

            # Wait for result (with timeout)
            result = await asyncio.wait_for(
                asyncio.to_thread(poller.result),
                timeout=120.0  # 2 minute timeout
            )

            # Extract content
            extracted_data = self._process_result(result)
            extracted_data["file_hash"] = content_hash
            extracted_data["model_used"] = model_id
            extracted_data["analyzed_at"] = datetime.utcnow().isoformat()

            logger.info(
                f"Analysis complete: {len(extracted_data.get('text', ''))} chars, "
                f"{extracted_data.get('page_count', 0)} pages"
            )

            return extracted_data

        except asyncio.TimeoutError:
            logger.error(f"Analysis timed out for: {file_path}")
            return {"error": "Analysis timed out", "text": ""}
        except Exception as e:
            logger.error(f"Error analyzing document {file_path}: {e}")
            return {"error": str(e), "text": ""}

    def _process_result(self, result) -> Dict[str, Any]:
        """
        Process Azure analysis result into structured data.

        Args:
            result: Azure DocumentAnalysisResult

        Returns:
            Structured extraction result
        """
        # Extract full text
        text_content = []
        page_texts = []

        for page in result.pages:
            page_text_lines = []

            for line in page.lines:
                page_text_lines.append(line.content)

            page_text = "\n".join(page_text_lines)
            page_texts.append({
                "page_number": page.page_number,
                "text": page_text,
                "width": page.width,
                "height": page.height,
                "unit": page.unit,
                "words": len(page.words) if page.words else 0,
            })
            text_content.append(page_text)

        full_text = "\n\n".join(text_content)

        # Extract tables
        tables = []
        for table_idx, table in enumerate(result.tables):
            table_data = {
                "table_index": table_idx,
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": []
            }

            for cell in table.cells:
                table_data["cells"].append({
                    "row": cell.row_index,
                    "column": cell.column_index,
                    "content": cell.content,
                    "row_span": cell.row_span,
                    "column_span": cell.column_span,
                })

            tables.append(table_data)

        # Extract key-value pairs
        key_value_pairs = []
        if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
            for kv in result.key_value_pairs:
                if kv.key and kv.value:
                    key_value_pairs.append({
                        "key": kv.key.content,
                        "value": kv.value.content if kv.value else None,
                        "confidence": kv.confidence,
                    })

        # Extract document metadata
        metadata = {
            "api_version": result.api_version if hasattr(result, 'api_version') else None,
            "model_id": result.model_id if hasattr(result, 'model_id') else None,
        }

        # Calculate statistics
        total_words = sum(len(page.get("text", "").split()) for page in page_texts)
        total_chars = len(full_text)

        return {
            "text": full_text,
            "pages": page_texts,
            "page_count": len(page_texts),
            "tables": tables,
            "table_count": len(tables),
            "key_value_pairs": key_value_pairs,
            "word_count": total_words,
            "char_count": total_chars,
            "metadata": metadata,
            "confidence": self._calculate_average_confidence(result),
        }

    def _calculate_average_confidence(self, result) -> float:
        """Calculate average confidence score across all pages."""
        confidences = []

        for page in result.pages:
            if page.words:
                for word in page.words:
                    if hasattr(word, 'confidence') and word.confidence is not None:
                        confidences.append(word.confidence)

        return sum(confidences) / len(confidences) if confidences else 0.0

    async def extract_text_from_image(
        self,
        image_path: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract text from an image using OCR.

        Args:
            image_path: Path to the image
            language: Language hint (e.g., "en", "es")

        Returns:
            Extracted text and metadata
        """
        result = await self.analyze_document(
            file_path=image_path,
            model_id="prebuilt-read"
        )

        if "error" not in result:
            result["document_type"] = "image"

        return result

    async def extract_with_layout(
        self,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Extract document with full layout analysis.

        Includes tables, key-value pairs, and document structure.

        Args:
            file_path: Path to the document

        Returns:
            Full layout analysis result
        """
        return await self.analyze_document(
            file_path=file_path,
            model_id="prebuilt-layout"
        )

    async def batch_analyze(
        self,
        file_paths: List[str],
        model_id: str = "prebuilt-read",
        max_concurrent: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple documents concurrently.

        Args:
            file_paths: List of file paths
            model_id: Azure model to use
            max_concurrent: Maximum concurrent analyses

        Returns:
            List of analysis results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(path: str) -> Dict[str, Any]:
            async with semaphore:
                result = await self.analyze_document(path, model_id)
                result["file_path"] = path
                return result

        tasks = [analyze_with_semaphore(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "file_path": file_paths[i],
                    "error": str(result),
                    "text": ""
                })
            else:
                processed_results.append(result)

        return processed_results

    async def extract_text_for_classification(
        self,
        file_path: str,
        max_chars: int = 15000,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text optimized for AI classification.

        Returns truncated text suitable for LLM processing along with metadata.

        Args:
            file_path: Path to the document
            max_chars: Maximum characters to return

        Returns:
            Tuple of (text, metadata)
        """
        result = await self.analyze_document(file_path)

        if "error" in result:
            return "", result

        text = result.get("text", "")

        # Truncate if necessary
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[TRUNCATED]"

        metadata = {
            "page_count": result.get("page_count", 0),
            "word_count": result.get("word_count", 0),
            "table_count": result.get("table_count", 0),
            "confidence": result.get("confidence", 0),
            "truncated": len(result.get("text", "")) > max_chars,
        }

        return text, metadata


# Singleton instance
_ocr_service: Optional[AzureDocumentIntelligenceOCR] = None


def get_azure_ocr_service() -> AzureDocumentIntelligenceOCR:
    """Get or create the Azure OCR service singleton."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = AzureDocumentIntelligenceOCR()
    return _ocr_service


async def initialize_azure_ocr() -> bool:
    """Initialize the Azure OCR service."""
    service = get_azure_ocr_service()
    return await service.initialize()
