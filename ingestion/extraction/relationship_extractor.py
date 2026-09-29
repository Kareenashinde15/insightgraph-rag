import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ingestion.extraction.entity_extractor import ExtractedEntity

class ExtractedRelationship(BaseModel):
    source_entity: str
    relationship: str
    target_entity: str
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    source_document: str
    source_chunk: str
    source_page: Optional[int] = 1
    extraction_method: str = "hybrid_rule_and_dependency"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    original_text: Optional[str] = None

class RelationshipExtractor:
    # Explicit linguistic and syntactic patterns for relationships
    REL_PATTERNS = [
        # WORKED_AT: [Person] worked at / joined / employed by [Company]
        (
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:worked\s+at|was\s+employed\s+at|joined|is\s+employed\s+at|served\s+at)\s+([A-Z][a-zA-Z0-9_\s]+?)(?:\s+(?:from|in|since|\.|\,|$))",
            "WORKED_AT",
            "PERSON",
            "COMPANY",
        ),
        # WORKED_ON: [Person] worked on / contributed to [Project]
        (
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:worked\s+on|contributed\s+to|collaborated\s+on|helped\s+build)\s+([A-Z][a-zA-Z0-9_\s]+?)(?:\s+(?:using|with|\.|\,|$))",
            "WORKED_ON",
            "PERSON",
            "PROJECT",
        ),
        # DEVELOPED / CREATED: [Person] developed / created / built / designed [Project/Tech]
        (
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:developed|created|built|designed|engineered|architected)\s+([A-Z][a-zA-Z0-9_\s]+?)(?:\s+(?:using|with|at|\.|\,|$))",
            "DEVELOPED",
            "PERSON",
            "PROJECT",
        ),
        # LED / MANAGED: [Person] led / managed / directed [Project/Team]
        (
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:led|managed|directed|supervised)\s+([A-Z][a-zA-Z0-9_\s]+?)(?:\s+(?:from|at|\.|\,|$))",
            "LED",
            "PERSON",
            "PROJECT",
        ),
        # USES / BUILT_WITH: [Project] uses / was built with / leverages [Tech/Database/Lang]
        (
            r"([A-Z][a-zA-Z0-9_\s]+?)\s+(?:uses|is\s+built\s+with|leverages|utilized|is\s+powered\s+by|adopted)\s+([A-Z][a-zA-Z0-9_.+#\s]+?)(?:\s+(?:for|and|\.|\,|$))",
            "USES",
            "PROJECT",
            "TECHNOLOGY",
        ),
        # PART_OF: [Project] is part of [Org/Company]
        (
            r"([A-Z][a-zA-Z0-9_\s]+?)\s+(?:is\s+part\s+of|belongs\s+to|falls\s+under)\s+([A-Z][a-zA-Z0-9_\s]+?)(?:\s+(?:\.|\,|$))",
            "PART_OF",
            "PROJECT",
            "ORGANIZATION",
        ),
        # LOCATED_IN: [Company/Org] located in / headquartered in [Location]
        (
            r"([A-Z][a-zA-Z0-9_\s]+?)\s+(?:is\s+located\s+in|headquartered\s+in|based\s+in)\s+([A-Z][a-zA-Z0-9_\s]+?)(?:\s+(?:\.|\,|$))",
            "LOCATED_IN",
            "ORGANIZATION",
            "LOCATION",
        ),
    ]

    def extract_dates(self, sentence: str) -> tuple[Optional[str], Optional[str]]:
        # Check patterns like "2020-2023", "from 2019 to 2022", "since 2021"
        range_match = re.search(r"\b(20\d\d)\s*(?:-|–|to)\s*(20\d\d)\b", sentence)
        if range_match:
            return range_match.group(1), range_match.group(2)
        single_match = re.search(r"\b(?:in|since|from)\s+(20\d\d)\b", sentence)
        if single_match:
            return single_match.group(1), None
        return None, None

    def extract_relationships(
        self,
        text: str,
        entities: List[ExtractedEntity],
        document_id: str,
        chunk_id: str,
        page_number: int = 1,
    ) -> List[ExtractedRelationship]:
        relationships: List[ExtractedRelationship] = []
        entity_names_map = {e.name.lower(): e for e in entities}
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sent in sentences:
            s_clean = sent.strip()
            if not s_clean:
                continue

            start_yr, end_yr = self.extract_dates(s_clean)

            # 1. Regex Pattern Matching
            for pat, rel_type, def_src_type, def_tgt_type in self.REL_PATTERNS:
                matches = re.finditer(pat, s_clean, re.IGNORECASE)
                for m in matches:
                    src_str = m.group(1).strip()
                    tgt_str = m.group(2).strip()

                    # Match with extracted entities or accept normalized
                    matched_src = None
                    matched_tgt = None

                    for name_l, ent in entity_names_map.items():
                        if name_l == src_str.lower() or name_l in src_str.lower() or src_str.lower() in name_l:
                            matched_src = ent.name
                        if name_l == tgt_str.lower() or name_l in tgt_str.lower() or tgt_str.lower() in name_l:
                            matched_tgt = ent.name

                    if not matched_src and len(src_str) > 2:
                        matched_src = src_str
                    if not matched_tgt and len(tgt_str) > 2:
                        matched_tgt = tgt_str

                    if matched_src and matched_tgt and matched_src.lower() != matched_tgt.lower():
                        # Exclude common false positives
                        if matched_src.lower() not in ["the", "this", "that", "it", "they"] and matched_tgt.lower() not in ["the", "this", "that", "it", "they"]:
                            relationships.append(
                                ExtractedRelationship(
                                    source_entity=matched_src,
                                    relationship=rel_type,
                                    target_entity=matched_tgt,
                                    confidence=0.92,
                                    source_document=document_id,
                                    source_chunk=chunk_id,
                                    source_page=page_number,
                                    extraction_method="syntactic_pattern",
                                    start_date=start_yr,
                                    end_date=end_yr,
                                    original_text=s_clean,
                                )
                            )

            # 2. Co-occurrence and syntactic linking between recognized entities in same sentence
            sent_entities = [e for e in entities if e.name.lower() in s_clean.lower()]
            if len(sent_entities) >= 2:
                # E.g. If sentence has PERSON and COMPANY and contains "at", "with", "work"
                people = [e for e in sent_entities if e.type == "PERSON"]
                companies = [e for e in sent_entities if e.type in ["COMPANY", "ORGANIZATION"]]
                projects = [e for e in sent_entities if e.type == "PROJECT"]
                techs = [e for e in sent_entities if e.type in ["PROGRAMMING_LANGUAGE", "DATABASE", "FRAMEWORK", "TECHNOLOGY"]]

                for p in people:
                    for c in companies:
                        if any(w in s_clean.lower() for w in ["work", "employed", "joined", "lead", "engineer", "at"]):
                            relationships.append(
                                ExtractedRelationship(
                                    source_entity=p.name,
                                    relationship="WORKED_AT",
                                    target_entity=c.name,
                                    confidence=0.94,
                                    source_document=document_id,
                                    source_chunk=chunk_id,
                                    source_page=page_number,
                                    extraction_method="cooccurrence_linking",
                                    start_date=start_yr,
                                    end_date=end_yr,
                                    original_text=s_clean,
                                )
                            )
                    for pr in projects:
                        if any(w in s_clean.lower() for w in ["worked on", "lead", "built", "developed", "created", "on"]):
                            rel_name = "DEVELOPED" if any(w in s_clean.lower() for w in ["built", "developed", "created"]) else "WORKED_ON"
                            relationships.append(
                                ExtractedRelationship(
                                    source_entity=p.name,
                                    relationship=rel_name,
                                    target_entity=pr.name,
                                    confidence=0.93,
                                    source_document=document_id,
                                    source_chunk=chunk_id,
                                    source_page=page_number,
                                    extraction_method="cooccurrence_linking",
                                    start_date=start_yr,
                                    end_date=end_yr,
                                    original_text=s_clean,
                                )
                            )

                for pr in projects:
                    for t in techs:
                        if any(w in s_clean.lower() for w in ["use", "built with", "implemented", "stack", "powered", "written"]):
                            relationships.append(
                                ExtractedRelationship(
                                    source_entity=pr.name,
                                    relationship="USES",
                                    target_entity=t.name,
                                    confidence=0.95,
                                    source_document=document_id,
                                    source_chunk=chunk_id,
                                    source_page=page_number,
                                    extraction_method="tech_stack_linking",
                                    original_text=s_clean,
                                )
                            )

                # Safe generic fallback: record co-occurrence rather than
                # inventing a semantic relationship for arbitrary documents.
                for left_index, left in enumerate(sent_entities[:6]):
                    for right in sent_entities[left_index + 1:6]:
                        relationships.append(
                            ExtractedRelationship(
                                source_entity=left.name,
                                relationship="MENTIONED_WITH",
                                target_entity=right.name,
                                confidence=0.60,
                                source_document=document_id,
                                source_chunk=chunk_id,
                                source_page=page_number,
                                extraction_method="document_cooccurrence",
                                original_text=s_clean,
                            )
                        )

        # Deduplicate relationships by (src, rel, tgt)
        deduped: List[ExtractedRelationship] = []
        seen = set()
        for r in relationships:
            key = (r.source_entity.lower(), r.relationship.upper(), r.target_entity.lower())
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        return deduped
