import re
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from backend.app.graph.graph_engine import GraphEngine

class QueryPlanStep(BaseModel):
    step_number: int
    action: str
    target_entity: Optional[str] = None
    target_type: Optional[str] = None
    relationship: Optional[str] = None
    description: str

class QueryPlan(BaseModel):
    query: str
    query_type: str  # SEMANTIC, GRAPH, HYBRID
    steps: List[QueryPlanStep]
    identified_entities: List[str]
    identified_relations: List[str]

class QueryPlanner:
    def __init__(self, graph_engine: GraphEngine):
        self.graph_engine = graph_engine

    def identify_entities_in_query(self, query: str) -> List[str]:
        found = []
        # Check all existing nodes in graph
        for node in self.graph_engine.get_all_nodes():
            pattern = rf"\b{re.escape(node.name)}\b"
            if re.search(pattern, query, re.IGNORECASE):
                found.append(node.name)
            else:
                for alias in node.aliases:
                    if re.search(rf"\b{re.escape(alias)}\b", query, re.IGNORECASE):
                        found.append(node.name)
                        break

        return list(dict.fromkeys(found))

    def create_plan(self, query: str, query_type: str) -> QueryPlan:
        entities = self.identify_entities_in_query(query)
        steps: List[QueryPlanStep] = []
        q_lower = query.lower()

        step_num = 1

        if len(entities) >= 1:
            for ent in entities:
                steps.append(
                    QueryPlanStep(
                        step_number=step_num,
                        action="GRAPH_LOOKUP",
                        target_entity=ent,
                        description=f"Resolve entity '{ent}' in Knowledge Graph and retrieve immediate neighbors and relationships.",
                    )
                )
                step_num += 1

            steps.append(
                QueryPlanStep(
                    step_number=step_num,
                    action="MULTI_HOP_TRAVERSAL",
                    description=f"Traverse up to 3 hops from {', '.join(entities)} when optional graph data is available.",
                )
            )
            step_num += 1

            steps.append(
                QueryPlanStep(
                    step_number=step_num,
                    action="VECTOR_RETRIEVAL",
                    description=f"Perform local semantic search for query passages relevant to {', '.join(entities)}.",
                )
            )
            step_num += 1

            steps.append(
                QueryPlanStep(
                    step_number=step_num,
                    action="RERANK_AND_ASSEMBLE",
                    description="Merge graph facts with retrieved vector chunks and assemble structured evidence context.",
                )
            )
            step_num += 1

            steps.append(
                QueryPlanStep(
                    step_number=step_num,
                    action="GENERATE_GROUNDED_ANSWER",
                    description="Generate factual response with strict document citations and graph paths.",
                )
            )
        else:
            steps = [
                QueryPlanStep(
                    step_number=1,
                    action="VECTOR_RETRIEVAL",
                    description="Query the local vector index for top-K semantically relevant document chunks.",
                ),
                QueryPlanStep(
                    step_number=2,
                    action="GENERATE_GROUNDED_ANSWER",
                    description="Formulate grounded answer citing supporting source passages.",
                )
            ]

        return QueryPlan(
            query=query,
            query_type=query_type,
            steps=steps,
            identified_entities=entities,
            identified_relations=[],
        )
