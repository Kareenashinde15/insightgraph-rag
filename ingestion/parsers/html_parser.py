from bs4 import BeautifulSoup
from typing import List
from ingestion.parsers.base import BaseParser, ParsedDocument, ParsedChunkDraft

class HTMLParser(BaseParser):
    def parse(self, file_path: str, filename: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            html_text = f.read()

        soup = BeautifulSoup(html_text, "html.parser")
        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.extract()

        drafts: List[ParsedChunkDraft] = []
        current_section = "General"
        current_page = 1

        headings_and_paras = soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "div"])
        current_block: List[str] = []

        for elem in headings_and_paras:
            text = elem.get_text().strip()
            if not text:
                continue

            element_name = getattr(elem, "name", None)
            if element_name in ["h1", "h2", "h3", "h4"]:
                if current_block:
                    drafts.append(
                        ParsedChunkDraft(
                            page_number=current_page,
                            section=current_section,
                            paragraph="\n".join(current_block),
                            text="\n".join(current_block),
                        )
                    )
                    current_block = []
                current_section = text
                if len(drafts) % 4 == 0 and len(drafts) > 0:
                    current_page += 1
            else:
                current_block.append(text)
                if len(current_block) >= 3:
                    drafts.append(
                        ParsedChunkDraft(
                            page_number=current_page,
                            section=current_section,
                            paragraph="\n".join(current_block),
                            text="\n".join(current_block),
                        )
                    )
                    current_block = []

        if current_block:
            drafts.append(
                ParsedChunkDraft(
                    page_number=current_page,
                    section=current_section,
                    paragraph="\n".join(current_block),
                    text="\n".join(current_block),
                )
            )

        raw_text = soup.get_text(separator="\n").strip()
        if not drafts:
            drafts.append(
                ParsedChunkDraft(
                    page_number=1,
                    section="Document",
                    paragraph=raw_text,
                    text=raw_text,
                )
            )

        return ParsedDocument(
            filename=filename,
            file_type="html",
            raw_text=raw_text,
            pages=drafts,
            metadata={"title": soup.title.string if soup.title else filename},
        )
