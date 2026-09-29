import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DocumentChunkModel(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    page_number: Optional[int] = 1
    section: Optional[str] = "General"
    paragraph: Optional[str] = ""
    text: str
    token_count: int = 0
    entities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConfigurableChunker:
    def __init__(self, target_chunk_size: int = 500, overlap_size: int = 100):
        """
        target_chunk_size in approximate words/tokens.
        overlap_size in approximate words/tokens.
        """
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def count_tokens_approx(self, text: str) -> int:
        # Fast approximation ~1.3 tokens per whitespace-separated word
        words = text.split()
        return int(len(words) * 1.3)

    def chunk_document(self, document_id: str, parsed_drafts: list) -> List[DocumentChunkModel]:
        chunks: List[DocumentChunkModel] = []
        chunk_idx = 1

        for draft in parsed_drafts:
            draft_text = draft.text.strip()
            if not draft_text:
                continue

            words = draft_text.split()
            # If draft text is within reasonable size, keep it as an atomic structural chunk
            if len(words) <= self.target_chunk_size:
                chunks.append(
                    DocumentChunkModel(
                        id=f"{document_id}_chunk_{chunk_idx:03d}",
                        document_id=document_id,
                        chunk_index=chunk_idx,
                        page_number=draft.page_number,
                        section=draft.section or "General",
                        paragraph=draft.paragraph or draft_text[:100],
                        text=draft_text,
                        token_count=self.count_tokens_approx(draft_text),
                        metadata=draft.metadata or {},
                    )
                )
                chunk_idx += 1
            else:
                # Sliding window preserving overlap
                step = max(50, self.target_chunk_size - self.overlap_size)
                for start_i in range(0, len(words), step):
                    window_words = words[start_i: start_i + self.target_chunk_size]
                    if not window_words:
                        break
                    chunk_text = " ".join(window_words)
                    chunks.append(
                        DocumentChunkModel(
                            id=f"{document_id}_chunk_{chunk_idx:03d}",
                            document_id=document_id,
                            chunk_index=chunk_idx,
                            page_number=draft.page_number,
                            section=draft.section or "General",
                            paragraph=draft.paragraph or chunk_text[:100],
                            text=chunk_text,
                            token_count=self.count_tokens_approx(chunk_text),
                            metadata=draft.metadata or {},
                        )
                    )
                    chunk_idx += 1
                    if start_i + self.target_chunk_size >= len(words):
                        break

        # Fallback if no chunks generated
        if not chunks:
            chunks.append(
                DocumentChunkModel(
                    id=f"{document_id}_chunk_001",
                    document_id=document_id,
                    chunk_index=1,
                    page_number=1,
                    section="Document",
                    paragraph="",
                    text="Empty document content",
                    token_count=3,
                )
            )

        return chunks
