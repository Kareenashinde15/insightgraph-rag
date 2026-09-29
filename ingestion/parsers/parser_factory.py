import os
from ingestion.parsers.base import BaseParser, ParsedDocument
from ingestion.parsers.text_parser import TextParser
from ingestion.parsers.html_parser import HTMLParser
from ingestion.parsers.pdf_parser import PDFParser
from ingestion.parsers.docx_parser import DocxParser

class ParserFactory:
    @staticmethod
    def get_parser(filename: str) -> BaseParser:
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".pdf"]:
            return PDFParser()
        elif ext in [".docx", ".doc"]:
            return DocxParser()
        elif ext in [".html", ".htm"]:
            return HTMLParser()
        elif ext in [".txt", ".md", ".markdown", ".csv", ".json", ".log"]:
            return TextParser()
        else:
            # Fallback to TextParser
            return TextParser()

    @classmethod
    def parse_file(cls, file_path: str, filename: str) -> ParsedDocument:
        parser = cls.get_parser(filename)
        return parser.parse(file_path, filename)
