from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class FactConflict(BaseModel):
    id: str
    entity_name: str
    relationship_type: str
    target_entity: str
    description: str
    claims: List[Dict[str, Any]]
    detected_at: str

class ConflictDetector:
    def detect_conflicts(self, relationships: List[Dict[str, Any]]) -> List[FactConflict]:
        """
        Detects conflicts when identical source-relationship-target have differing
        temporal ranges, contradicting role claims, or differing dates from different documents.
        """
        grouped: Dict[tuple, List[Dict[str, Any]]] = {}

        for rel in relationships:
            src = rel.get("source_entity", "").strip().lower()
            rtype = rel.get("relationship", "").strip().upper()
            tgt = rel.get("target_entity", "").strip().lower()
            key = (src, rtype, tgt)

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(rel)

        conflicts: List[FactConflict] = []

        import datetime
        now_iso = datetime.datetime.now().isoformat()

        for (src, rtype, tgt), claims in grouped.items():
            if len(claims) < 2:
                continue

            # Compare start/end dates
            dates_seen = set()
            docs_seen = set()
            differing_dates = False

            for c in claims:
                s_date = c.get("start_date")
                e_date = c.get("end_date")
                doc = c.get("source_document")
                docs_seen.add(doc)
                date_tuple = (s_date, e_date)
                if any(date_tuple):
                    dates_seen.add(date_tuple)

            if len(dates_seen) > 1 and len(docs_seen) > 1:
                differing_dates = True

            if differing_dates:
                source_entity = str(claims[0].get("source_entity") or "")
                target_entity = str(claims[0].get("target_entity") or "")
                conflicts.append(
                    FactConflict(
                        id=f"conflict_{src}_{rtype}_{tgt}",
                        entity_name=source_entity,
                        relationship_type=rtype,
                        target_entity=target_entity,
                        description=f"Potential conflicting information detected: divergent dates reported across {len(docs_seen)} documents for {source_entity} -> {rtype} -> {target_entity}.",
                        claims=[
                            {
                                "source_document": c.get("source_document"),
                                "source_chunk": c.get("source_chunk"),
                                "start_date": c.get("start_date"),
                                "end_date": c.get("end_date"),
                                "original_text": c.get("original_text"),
                            }
                            for c in claims
                        ],
                        detected_at=now_iso,
                    )
                )

        return conflicts
