"""Validate model citations against evidence actually retrieved for the query."""

import re
from typing import Any, Dict, List, Tuple


class CitationValidator:
    """Keep citations grounded in the current retrieval result.

    The LLM can format or reorder citations, but it cannot introduce a chunk
    that was not supplied in the prompt. This is intentionally independent of
    any provider so changing LLM vendors cannot weaken grounding guarantees.
    """

    MARKER_PATTERN = re.compile(r"\[(\d+)\]")

    def validate(
        self,
        answer: str,
        citations: List[Dict[str, Any]],
        retrieval_result: Any,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        chunks = list(getattr(retrieval_result, "vector_chunks", []) or [])
        allowed = {chunk.chunk_id: chunk for chunk in chunks}
        accepted: List[Dict[str, Any]] = []
        issues: List[str] = []
        seen_chunks = set()

        for raw in citations or []:
            chunk_id = str(raw.get("chunk_id", ""))
            chunk = allowed.get(chunk_id)
            if not chunk:
                issues.append(f"Dropped citation for unretrieved chunk '{chunk_id or 'unknown'}'.")
                continue
            if raw.get("document_id") and raw.get("document_id") != chunk.document_id:
                issues.append(f"Dropped citation with mismatched document for chunk '{chunk_id}'.")
                continue
            if chunk_id in seen_chunks:
                continue

            seen_chunks.add(chunk_id)
            citation = dict(raw)
            citation.update(
                {
                    "citation_index": len(accepted) + 1,
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "page": chunk.page or 1,
                    "document_name": chunk.source or chunk.document_id,
                    "snippet": chunk.text[:500],
                    "similarity_score": chunk.similarity,
                }
            )
            accepted.append(citation)

        markers = [int(match.group(1)) for match in self.MARKER_PATTERN.finditer(answer or "")]
        invalid_markers = sorted({marker for marker in markers if marker < 1 or marker > len(accepted)})
        if invalid_markers:
            issues.append(
                "Answer referenced citation marker(s) without matching evidence: "
                + ", ".join(f"[{marker}]" for marker in invalid_markers)
                + "."
            )

        result = {
            "valid": not issues,
            "input_count": len(citations or []),
            "accepted_count": len(accepted),
            "rejected_count": max(0, len(citations or []) - len(accepted)),
            "invalid_markers": invalid_markers,
            "issues": issues,
        }
        return accepted, result
