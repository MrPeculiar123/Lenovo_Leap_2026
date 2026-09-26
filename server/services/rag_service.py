"""
RAG Service (Production Pinecone Vector DB & Gemini Embedding 2)
==============================================================
Queries Pinecone using 1536-dim Gemini Embedding 2 (gemini-embedding-2-preview)
via the official google-genai SDK to ground AI Tutor responses and study planning.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone
try:
    from core.config import settings
    from services.resilience import retry_call
except ImportError:
    from server.core.config import settings
    from server.services.resilience import retry_call

try:
    from core.logger import workflow_log
except ImportError:
    from server.core.logger import workflow_log

# Ensure environment variables are loaded
for env_path in [Path("server/.env"), Path(".env"), Path(__file__).parent.parent / ".env"]:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break


@dataclass
class EducationalResource:
    """An educational article, video, cheat sheet, or code snippet."""
    id: str
    concept_id: str
    title: str
    resource_type: str  # "article" | "video" | "interactive_exercise" | "cheat_sheet"
    url_or_ref: str
    content_snippet: str
    estimated_minutes: int
    difficulty: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "concept_id": self.concept_id,
            "title": self.title,
            "resource_type": self.resource_type,
            "url_or_ref": self.url_or_ref,
            "content_snippet": self.content_snippet,
            "estimated_minutes": self.estimated_minutes,
            "difficulty": self.difficulty,
            "tags": self.tags
        }


class RAGService:
    """
    Production RAG service querying Pinecone Vector DB via 1536-dim Gemini Embedding 2.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.concept_index: Dict[str, List[EducationalResource]] = {}
        self._load_local_concept_map(data_path)

        # Initialize Pinecone Client
        self.pinecone_api_key = os.environ.get("PINECONE_API_KEY", "")
        self.index_name = os.environ.get("PINECONE_INDEX_NAME", "pathforge-educational-content")
        self.pinecone_index = None

        if self.pinecone_api_key:
            try:
                self.pc = Pinecone(api_key=self.pinecone_api_key)
                self.pinecone_index = self.pc.Index(self.index_name)
            except Exception as e:
                workflow_log(logging.WARNING, "[RAG]", operation="pinecone_init", status="fallback")

        # Initialize Google GenAI Client (official SDK)
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.genai_client = None
        if self.gemini_api_key:
            try:
                self.genai_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                workflow_log(logging.WARNING, "[RAG]", operation="embedding_init", status="fallback")

    def _resolve_data_path(self, data_path: Optional[str] = None) -> Path:
        """Finds educational_content.json across common execution directories."""
        if data_path:
            return Path(data_path)

        candidates = [
            Path(__file__).parent.parent / "data" / "educational_content.json",
            Path("server/data/educational_content.json"),
            Path("data/educational_content.json"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        raise FileNotFoundError("Could not find 'server/data/educational_content.json'.")

    def _load_local_concept_map(self, data_path: Optional[str] = None) -> None:
        """Loads local index for instant O(1) concept lookup."""
        file_path = self._resolve_data_path(data_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("resources", []):
            res = EducationalResource(
                id=item["id"],
                concept_id=item["concept_id"],
                title=item["title"],
                resource_type=item["resource_type"],
                url_or_ref=item.get("url_or_ref", ""),
                content_snippet=item["content_snippet"],
                estimated_minutes=int(item.get("estimated_minutes", 15)),
                difficulty=item.get("difficulty", "intermediate"),
                tags=item.get("tags", [])
            )
            cid = res.concept_id.strip().lower()
            if cid not in self.concept_index:
                self.concept_index[cid] = []
            self.concept_index[cid].append(res)

    def search_by_concept(self, concept_id: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Instant O(1) concept lookup for root-cause prerequisite gaps."""
        items = self.concept_index.get(concept_id.strip().lower(), [])
        results = [r.to_dict() for r in items[:limit]]
        workflow_log(logging.DEBUG, "[RAG]", query_type="concept", result_count=len(results))
        return results

    def search_by_query(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Performs dense vector search against Pinecone using 1536-dim gemini-embedding-2-preview."""
        if not query.strip() or not self.pinecone_index or not self.genai_client:
            return []

        started_at = time.perf_counter()
        try:
            resp = retry_call(
                lambda: self.genai_client.models.embed_content(
                    model="gemini-embedding-2-preview",
                    contents=query.strip(),
                    config=types.EmbedContentConfig(output_dimensionality=1536)
                ),
                retries=settings.EXTERNAL_CALL_RETRIES,
            )
            query_vector = resp.embeddings[0].values

            response = retry_call(
                lambda: self.pinecone_index.query(
                    vector=query_vector,
                    top_k=limit,
                    include_metadata=True
                ),
                retries=settings.EXTERNAL_CALL_RETRIES,
            )

            results = []
            for match in response.matches:
                meta = match.metadata or {}
                item = {
                    "id": match.id,
                    "concept_id": meta.get("concept_id", ""),
                    "title": meta.get("title", ""),
                    "resource_type": meta.get("resource_type", ""),
                    "url_or_ref": meta.get("url_or_ref", ""),
                    "content_snippet": meta.get("content_snippet", ""),
                    "estimated_minutes": int(meta.get("estimated_minutes", 15)),
                    "difficulty": meta.get("difficulty", "intermediate"),
                    "tags": meta.get("tags", []),
                    "similarity_score": round(float(match.score), 3)
                }
                results.append(item)

            workflow_log(logging.INFO, "[RAG]", query_type="vector", result_count=len(results), top_score=results[0].get("similarity_score") if results else None, duration_ms=round((time.perf_counter() - started_at) * 1000))
            return results
        except Exception as e:
            workflow_log(logging.WARNING, "[RAG]", query_type="vector", status="fallback", duration_ms=round((time.perf_counter() - started_at) * 1000))
            return []

    def get_resources_for_gaps(
        self, gap_concept_ids: List[str], max_per_concept: int = 2
    ) -> List[Dict[str, Any]]:
        """Batch-retrieves educational materials for prioritized root-cause gaps."""
        gathered: List[Dict[str, Any]] = []
        seen_ids = set()
        for cid in gap_concept_ids:
            items = self.search_by_concept(cid, limit=max_per_concept)
            for item in items:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    gathered.append(item)
        return gathered

    retrieve_for_gaps = get_resources_for_gaps

    def format_context_for_prompt(self, resources: List[Dict[str, Any]]) -> str:
        """Formats retrieved educational chunks into clean Markdown context for LLM prompts."""
        if not resources:
            return "No specific reference documents retrieved."

        lines = ["### Grounded Educational Context (Source Curriculum):\n"]
        for idx, res in enumerate(resources, 1):
            lines.append(f"**Document {idx}: {res['title']}** (Type: {res['resource_type']}, Est. Time: {res['estimated_minutes']} mins)")
            lines.append(f"Content: {res['content_snippet']}")
            if res.get("url_or_ref"):
                lines.append(f"Source Reference: {res['url_or_ref']}")
            lines.append("")

        return "\n".join(lines)


# Global singleton instance
rag_service = RAGService()
