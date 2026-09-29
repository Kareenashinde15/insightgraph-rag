import re
from typing import Tuple, List

class QueryClassifier:
    GRAPH_PATTERNS = [
        r"\bwho\s+(?:worked|joined|led|managed|built|developed|created|knows)\b",
        r"\bwhich\s+(?:projects?|people|companies|organizations?|technologies?)\s+(?:used|involved|connected|worked)\b",
        r"\bconnections?\s+between\b",
        r"\brelationship\s+between\b",
        r"\bpath\s+from\b",
        r"\bwhere\s+did\s+[A-Z][a-z]+\s+work\b",
        r"\bwho\s+is\s+connected\s+to\b",
    ]

    SEMANTIC_PATTERNS = [
        r"\bsummarize\b",
        r"\bexplain\s+(?:how|what|why)\b",
        r"\btell\s+me\s+about\b",
        r"\bdescribe\b",
        r"\boverview\s+of\b",
        r"\bbackground\s+on\b",
    ]

    def classify(self, query: str) -> Tuple[str, float]:
        """
        Returns: (classification: 'SEMANTIC' | 'GRAPH' | 'HYBRID', confidence: float)
        """
        q = query.lower()

        # Multi-clause or multi-hop indicators strongly imply HYBRID
        has_multi_entity = len(re.findall(r"\b(?:and|with|both|also|who\s+also)\b", q)) > 0
        has_graph_indicator = any(re.search(pat, q, re.IGNORECASE) for pat in self.GRAPH_PATTERNS)
        has_semantic_indicator = any(re.search(pat, q, re.IGNORECASE) for pat in self.SEMANTIC_PATTERNS)

        if has_graph_indicator and (has_multi_entity or has_semantic_indicator or "project" in q or "company" in q or "technology" in q):
            return "HYBRID", 0.94

        if has_graph_indicator:
            return "GRAPH", 0.91

        if has_semantic_indicator and not has_graph_indicator:
            return "SEMANTIC", 0.89

        # Default to HYBRID for complex enterprise knowledge queries
        return "HYBRID", 0.85
