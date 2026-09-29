import re
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional, Any

class EntityNormalizer:
    # Common corporate suffixes and tech qualifiers
    ORG_SUFFIXES = [
        r"\binc\.?\b", r"\bllc\.?\b", r"\bcorp\.?\b", r"\bcorporation\b",
        r"\bltd\.?\b", r"\blimited\b", r"\bgmbh\b", r"\bco\.?\b", r"\bgroup\b"
    ]
    TECH_SUFFIXES = [
        r"\bprogramming\s+language\b", r"\blanguage\b", r"\bdatabase\b",
        r"\bframework\b", r"\blibrary\b", r"\btool\b", r"\bplatform\b"
    ]

    CANONICAL_SYNONYMS = {
        "python programming language": "Python",
        "python3": "Python",
        "python 3": "Python",
        "ts": "TypeScript",
        "typescript language": "TypeScript",
        "js": "JavaScript",
    }

    def normalize_name(self, name: str, entity_type: str = "") -> str:
        cleaned = name.strip()
        lower = cleaned.lower()

        # Check explicit synonyms
        if lower in self.CANONICAL_SYNONYMS:
            return self.CANONICAL_SYNONYMS[lower]

        # Strip company suffixes if COMPANY/ORGANIZATION
        if entity_type in ["COMPANY", "ORGANIZATION"]:
            for suf in self.ORG_SUFFIXES:
                cleaned = re.sub(suf, "", cleaned, flags=re.IGNORECASE).strip()

        # Strip tech suffixes if PROGRAMMING_LANGUAGE/DATABASE/TECHNOLOGY
        if entity_type in ["PROGRAMMING_LANGUAGE", "DATABASE", "FRAMEWORK", "TECHNOLOGY"]:
            for suf in self.TECH_SUFFIXES:
                cleaned = re.sub(suf, "", cleaned, flags=re.IGNORECASE).strip()

        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-_")
        return cleaned if cleaned else name

    def compute_similarity(self, name1: str, name2: str) -> float:
        n1 = name1.lower()
        n2 = name2.lower()
        if n1 == n2:
            return 1.0

        # Exact substring match
        if n1 in n2 or n2 in n1:
            ratio = len(min(n1, n2, key=len)) / len(max(n1, n2, key=len))
            if ratio > 0.6:
                return 0.90 + (ratio * 0.08)

        # Sequence matcher similarity
        return SequenceMatcher(None, n1, n2).ratio()

    def resolve_entity(
        self,
        candidate_name: str,
        candidate_type: str,
        existing_entities: List[Dict[str, Any]],
        threshold: float = 0.85
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Returns:
            (resolved_canonical_name, was_merged, existing_entity_id)
        """
        norm_name = self.normalize_name(candidate_name, candidate_type)

        best_match = None
        best_score = 0.0

        for existing in existing_entities:
            ex_name = existing["name"]
            ex_type = existing.get("type", "")

            # If types conflict significantly (e.g. PERSON vs COMPANY), do not merge
            c_type_u = (candidate_type or "").upper()
            ex_type_u = (ex_type or "").upper()
            if c_type_u and ex_type_u and c_type_u != ex_type_u:
                # allow ORGANIZATION & COMPANY interchangeability
                if not (c_type_u in ["ORGANIZATION", "COMPANY"] and ex_type_u in ["ORGANIZATION", "COMPANY"]):
                    continue

            score = self.compute_similarity(norm_name, ex_name)

            # Check aliases as well
            for alias in existing.get("aliases", []):
                alias_score = self.compute_similarity(norm_name, alias)
                if alias_score > score:
                    score = alias_score

            if score > best_score:
                best_score = score
                best_match = existing

        if best_match and best_score >= threshold:
            return best_match["name"], True, best_match.get("id")

        return norm_name, False, None
