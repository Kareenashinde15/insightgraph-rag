"""Models for vectorless lexical section retrieval."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TextSearchResult(BaseModel):
    section_id: str
    document_id: str
    text: str
    page: Optional[int] = 1
    source: Optional[str] = ""
    relevance: float = 0.0
    entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        """Compatibility alias for existing citation/frontend contracts."""
        return self.section_id

    @property
    def similarity(self) -> float:
        """Compatibility alias for the old UI's relevance display."""
        return self.relevance
