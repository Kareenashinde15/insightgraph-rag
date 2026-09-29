from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ParsedChunkDraft:
    page_number: Optional[int]
    section: Optional[str]
    paragraph: Optional[str]
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ParsedDocument:
    filename: str
    file_type: str
    raw_text: str
    pages: List[ParsedChunkDraft] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseParser:
    def parse(self, file_path: str, filename: str) -> ParsedDocument:
        raise NotImplementedError
