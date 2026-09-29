import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ExtractedEntity(BaseModel):
    name: str
    type: str
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    source_page: Optional[int] = 1
    source_chunk_id: Optional[str] = None
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)

class EntityExtractionResult(BaseModel):
    entities: List[ExtractedEntity]

class HybridEntityExtractor:
    # Common tech/framework/database catalogs for high-precision extraction
    KNOWN_LANGUAGES = {
        "python", "typescript", "javascript", "golang", "go", "rust", "c++", "c#", "java", "ruby", "php", "swift", "kotlin", "scala"
    }
    KNOWN_DATABASES = {
        "neo4j", "qdrant", "postgresql", "postgres", "redis", "mongodb", "mysql", "sqlite", "pinecone", "weaviate", "elasticsearch", "cassandra"
    }
    KNOWN_FRAMEWORKS = {
        "react", "next.js", "nextjs", "vue", "angular", "fastapi", "flask", "django", "pytorch", "tensorflow", "celery", "express", "tailwind", "shadcn"
    }
    KNOWN_TECH = {
        "docker", "kubernetes", "git", "aws", "gcp", "azure", "linux", "graphql", "rest", "rag", "knowledge graph", "vector database", "embeddings", "llm"
    }
    GENERIC_ENTITY_STOPWORDS = {
        "the", "this", "that", "these", "those", "with", "from", "into", "over",
        "under", "through", "where", "when", "which", "page", "pages", "table",
        "figure", "contents", "introduction", "copyright", "document", "standard",
        "international", "all", "rights", "reserved", "none", "general",
    }
    def __init__(self, spacy_model: Optional[str] = "en_core_web_sm"):
        self.nlp = None
        if spacy_model:
            try:
                import spacy
                self.nlp = spacy.load(spacy_model)
            except Exception:
                self.nlp = None

    def extract_entities(self, text: str, page_number: int = 1, chunk_id: str = "") -> List[ExtractedEntity]:
        entity_map: Dict[str, ExtractedEntity] = {}

        def add_entity(name: str, etype: str, conf: float = 0.90, desc: str = ""):
            clean_name = name.strip().strip(".,;:()[]\"'")
            if not clean_name or len(clean_name) < 2:
                return
            key = clean_name.lower()
            if key not in entity_map or entity_map[key].confidence < conf:
                entity_map[key] = ExtractedEntity(
                    name=clean_name,
                    type=etype,
                    confidence=conf,
                    source_page=page_number,
                    source_chunk_id=chunk_id,
                    description=desc,
                )

        # 1. spaCy NER if available
        if self.nlp:
            try:
                doc = self.nlp(text[:4000]) # Cap for speed
                for ent in doc.ents:
                    lbl = ent.label_
                    val = ent.text.strip()
                    if lbl == "PERSON":
                        add_entity(val, "PERSON", 0.92)
                    elif lbl in ["ORG"]:
                        # Let the document determine the organization name;
                        # do not depend on a fixed company/demo catalog.
                        if any(marker in val.lower() for marker in ["inc", "corp", "llc", "ltd"]):
                            add_entity(val, "COMPANY", 0.94)
                        else:
                            add_entity(val, "ORGANIZATION", 0.88)
                    elif lbl in ["GPE", "LOC"]:
                        add_entity(val, "LOCATION", 0.90)
                    elif lbl == "DATE":
                        add_entity(val, "DATE", 0.85)
                    elif lbl == "PRODUCT":
                        add_entity(val, "PRODUCT", 0.88)
            except Exception:
                pass

        # 2. Regex and Domain Dictionary Matching for Technologies, Projects, Roles, Skills
        words_and_phrases = re.findall(r"\b[A-Za-z0-9_.+#-]+\b", text)
        for term in words_and_phrases:
            t_lower = term.lower()
            if t_lower in self.KNOWN_LANGUAGES:
                canonical = "Python" if t_lower == "python" else ("TypeScript" if t_lower == "typescript" else term.capitalize())
                add_entity(canonical, "PROGRAMMING_LANGUAGE", 0.97)
            elif t_lower in self.KNOWN_DATABASES:
                canonical = "Neo4j" if t_lower == "neo4j" else ("Qdrant" if t_lower == "qdrant" else term.capitalize())
                add_entity(canonical, "DATABASE", 0.96)
            elif t_lower in self.KNOWN_FRAMEWORKS:
                canonical = "Next.js" if t_lower in ["next.js", "nextjs"] else ("FastAPI" if t_lower == "fastapi" else term.capitalize())
                add_entity(canonical, "FRAMEWORK", 0.95)
            elif t_lower in self.KNOWN_TECH:
                add_entity(term, "TECHNOLOGY", 0.88)

        # 2b. Document-adaptive fallback for PDFs where an optional NER model
        # is unavailable. This recognizes stable identifiers and proper-name
        # phrases without relying on demo-specific company/person catalogs.
        for match in re.finditer(
            r"\b[A-Z]{2,}(?:/[A-Z]{2,})?(?:[-/]\d{2,4})?\b",
            text,
        ):
            value = match.group(0).strip()
            if value.lower() not in self.GENERIC_ENTITY_STOPWORDS and len(value) >= 2:
                entity_type = "STANDARD" if re.search(r"\d", value) else "ORGANIZATION"
                add_entity(value, entity_type, 0.78)

        for match in re.finditer(
            r"\b(?:[A-Z][a-z]{2,})(?:\s+[A-Z][a-z]{2,}){1,3}\b",
            text,
        ):
            value = match.group(0).strip()
            words = value.lower().split()
            if not any(word in self.GENERIC_ENTITY_STOPWORDS for word in words):
                add_entity(value, "CONCEPT", 0.70)

        for date_value in re.findall(
            r"\b(?:19|20)\d{2}(?:[-/]\d{1,2})?(?:[-/]\d{1,2})?\b",
            text,
        ):
            add_entity(date_value, "DATE", 0.82)

        # 3. Generic project-name patterns. No demo/project-name allowlist is
        # used, so this works with arbitrary user documents.
        project_patterns = [
            r"\b(Project\s+[A-Z][a-zA-Z0-9_-]+)\b",
            r"\bproject\s+called\s+([A-Z][a-zA-Z0-9_-]+)\b",
        ]
        for pat in project_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                proj_name = match.group(1).strip()
                add_entity(proj_name, "PROJECT", 0.95)

        # Standalone Project Names if capitalized in specific context (worked on Apollo, built Apollo)
        context_projects = re.findall(r"(?:worked\s+on|building|developed|launched|created|lead\s+on)\s+([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)?)", text)
        for cp in context_projects:
            cp_clean = cp.strip()
            if cp_clean.lower() not in self.KNOWN_LANGUAGES and cp_clean.lower() not in self.KNOWN_DATABASES and len(cp_clean) > 2:
                if not any(cp_clean.lower() == k for k in ["the", "a", "an"]):
                    add_entity(cp_clean, "PROJECT", 0.91)

        # 4. Role patterns (e.g. "Senior Software Engineer", "AI Researcher", "Tech Lead")
        role_matches = re.findall(r"\b(Senior\s+[A-Za-z\s]+Engineer|Software\s+Engineer|Research\s+Scientist|Data\s+Scientist|Product\s+Manager|Solutions\s+Architect|Tech\s+Lead|Engineering\s+Manager)\b", text, re.IGNORECASE)
        for rm in role_matches:
            add_entity(rm.strip().title(), "ROLE", 0.90)

        return list(entity_map.values())
