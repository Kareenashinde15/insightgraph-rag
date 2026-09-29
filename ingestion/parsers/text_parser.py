import re
from typing import List
from ingestion.parsers.base import BaseParser, ParsedDocument, ParsedChunkDraft

class TextParser(BaseParser):
    def parse(self, file_path: str, filename: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        file_type = "markdown" if filename.lower().endswith((".md", ".markdown")) else "txt"
        if filename.lower().endswith(".csv"):
            file_type = "csv"

        drafts: List[ParsedChunkDraft] = []
        current_section = "General"
        current_page = 1
        lines = content.splitlines()
        current_para: List[str] = []

        line_count = 0
        for line in lines:
            line_count += 1
            # Approximate page breaks every 45 lines for plain text / markdown
            if line_count > 45:
                current_page += 1
                line_count = 0

            # Detect Markdown headings
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                if current_para:
                    drafts.append(
                        ParsedChunkDraft(
                            page_number=current_page,
                            section=current_section,
                            paragraph="\n".join(current_para),
                            text="\n".join(current_para),
                        )
                    )
                    current_para = []
                current_section = heading_match.group(2).strip()
                continue

            if not line.strip():
                if current_para:
                    drafts.append(
                        ParsedChunkDraft(
                            page_number=current_page,
                            section=current_section,
                            paragraph="\n".join(current_para),
                            text="\n".join(current_para),
                        )
                    )
                    current_para = []
            else:
                current_para.append(line)

        if current_para:
            drafts.append(
                ParsedChunkDraft(
                    page_number=current_page,
                    section=current_section,
                    paragraph="\n".join(current_para),
                    text="\n".join(current_para),
                )
            )

        if not drafts:
            drafts.append(
                ParsedChunkDraft(
                    page_number=1,
                    section="Main",
                    paragraph=content,
                    text=content,
                )
            )

        return ParsedDocument(
            filename=filename,
            file_type=file_type,
            raw_text=content,
            pages=drafts,
            metadata={"total_lines": len(lines), "estimated_pages": current_page},
        )
