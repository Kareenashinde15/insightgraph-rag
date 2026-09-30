import re
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import deque
from backend.app.models.schema import GraphNodeModel, GraphEdgeModel

class GraphEngine:
    FORBIDDEN_CYPHER_KEYWORDS = [
        r"\bDELETE\b", r"\bDETACH\b", r"\bCREATE\b", r"\bSET\b",
        r"\bREMOVE\b", r"\bDROP\b", r"\bMERGE\b", r"\bALTER\b", r"\bINSERT\b"
    ]

    def __init__(self):
        self.nodes: Dict[str, GraphNodeModel] = {}
        self.edges: Dict[str, GraphEdgeModel] = {}
        # Adjacency maps
        self.out_edges: Dict[str, List[str]] = {}  # node_id -> [edge_id]
        self.in_edges: Dict[str, List[str]] = {}   # node_id -> [edge_id]
        self.name_to_id: Dict[str, str] = {}      # lowercase_name -> node_id

    def add_node(self, node: GraphNodeModel) -> GraphNodeModel:
        self.nodes[node.id] = node
        self.name_to_id[node.name.strip().lower()] = node.id
        self.name_to_id[node.normalized_name.strip().lower()] = node.id
        for alias in node.aliases:
            self.name_to_id[alias.strip().lower()] = node.id

        if node.id not in self.out_edges:
            self.out_edges[node.id] = []
        if node.id not in self.in_edges:
            self.in_edges[node.id] = []
        return node

    def add_edge(self, edge: GraphEdgeModel) -> GraphEdgeModel:
        self.edges[edge.id] = edge
        if edge.source not in self.out_edges:
            self.out_edges[edge.source] = []
        if edge.target not in self.in_edges:
            self.in_edges[edge.target] = []

        self.out_edges[edge.source].append(edge.id)
        self.in_edges[edge.target].append(edge.id)

        # Update source counts on connected nodes
        if edge.source in self.nodes:
            self.nodes[edge.source].source_count = max(self.nodes[edge.source].source_count, len(self.out_edges[edge.source]))
        if edge.target in self.nodes:
            self.nodes[edge.target].source_count = max(self.nodes[edge.target].source_count, len(self.in_edges[edge.target]))
        return edge

    def find_node_by_name(self, name: str) -> Optional[GraphNodeModel]:
        clean = name.strip().lower()
        if clean in self.name_to_id:
            return self.nodes.get(self.name_to_id[clean])
        # Substring fuzzy search
        for k, nid in self.name_to_id.items():
            if clean in k or k in clean:
                return self.nodes.get(nid)
        return None

    def get_all_nodes(self) -> List[GraphNodeModel]:
        return list(self.nodes.values())

    def get_all_edges(self) -> List[GraphEdgeModel]:
        return list(self.edges.values())

    def delete_by_document(self, document_id: str) -> None:
        """Remove provenance edges and orphaned nodes for a deleted document."""
        edge_ids = [eid for eid, edge in self.edges.items() if edge.source_document == document_id]
        for edge_id in edge_ids:
            edge = self.edges.pop(edge_id, None)
            if not edge:
                continue
            if edge_id in self.out_edges.get(edge.source, []):
                self.out_edges[edge.source].remove(edge_id)
            if edge_id in self.in_edges.get(edge.target, []):
                self.in_edges[edge.target].remove(edge_id)

        orphaned_ids = set()
        for node_id, node in self.nodes.items():
            if document_id in node.document_ids:
                node.document_ids.remove(document_id)
                if not node.document_ids:
                    orphaned_ids.add(node_id)

        # Remove any remaining edges attached to nodes that no longer have a source.
        dangling_edges = [
            eid for eid, edge in self.edges.items()
            if edge.source in orphaned_ids or edge.target in orphaned_ids
        ]
        for edge_id in dangling_edges:
            edge = self.edges.pop(edge_id)
            if edge_id in self.out_edges.get(edge.source, []):
                self.out_edges[edge.source].remove(edge_id)
            if edge_id in self.in_edges.get(edge.target, []):
                self.in_edges[edge.target].remove(edge_id)

        for node_id in orphaned_ids:
            node = self.nodes.pop(node_id, None)
            self.out_edges.pop(node_id, None)
            self.in_edges.pop(node_id, None)
            if node:
                names = [node.name, node.normalized_name, *node.aliases]
                for name in names:
                    if self.name_to_id.get(name.strip().lower()) == node_id:
                        self.name_to_id.pop(name.strip().lower(), None)

    def get_subgraph(self, node_id: str, depth: int = 1) -> Tuple[List[GraphNodeModel], List[GraphEdgeModel]]:
        if node_id not in self.nodes:
            return [], []

        visited_nodes: Set[str] = {node_id}
        visited_edges: Set[str] = set()
        queue = deque([(node_id, 0)])

        while queue:
            curr_id, curr_depth = queue.popleft()
            if curr_depth >= depth:
                continue

            # Outgoing edges
            for eid in self.out_edges.get(curr_id, []):
                edge = self.edges.get(eid)
                if edge is None:
                    continue
                visited_edges.add(eid)
                target_id = edge.target
                if target_id not in visited_nodes:
                    visited_nodes.add(target_id)
                    queue.append((target_id, curr_depth + 1))

            # Incoming edges
            for eid in self.in_edges.get(curr_id, []):
                edge = self.edges.get(eid)
                if edge is None:
                    continue
                visited_edges.add(eid)
                source_id = edge.source
                if source_id not in visited_nodes:
                    visited_nodes.add(source_id)
                    queue.append((source_id, curr_depth + 1))

        nodes_res = [self.nodes[nid] for nid in visited_nodes if nid in self.nodes]
        edges_res = [self.edges[eid] for eid in visited_edges if eid in self.edges]
        return nodes_res, edges_res

    def find_paths(
        self,
        start_node_id: str,
        end_node_id: Optional[str] = None,
        target_type: Optional[str] = None,
        max_hops: int = 3,
        relationship_filter: Optional[List[str]] = None
    ) -> List[List[Dict[str, str]]]:
        """
        Traverse up to max_hops from start_node_id.
        Returns paths formatted as list of hops:
        [{"source": "Alice", "relationship": "WORKED_ON", "target": "Apollo"}, ...]
        """
        if start_node_id not in self.nodes:
            return []

        results: List[List[Dict[str, str]]] = []
        # queue stores (current_node_id, current_path, visited_nodes)
        queue = deque([(start_node_id, [], {start_node_id})])

        while queue:
            curr_id, path, visited = queue.popleft()
            curr_node = self.nodes.get(curr_id)

            if len(path) > 0:
                # Check goal conditions
                if end_node_id and curr_id == end_node_id:
                    results.append(path)
                    continue
                elif target_type and curr_node and curr_node.type.upper() == target_type.upper():
                    results.append(path)
                elif not end_node_id and not target_type:
                    results.append(path)

            if len(path) >= max_hops:
                continue

            # Traverse out edges
            for eid in self.out_edges.get(curr_id, []):
                edge = self.edges.get(eid)
                if edge is None:
                    continue
                if relationship_filter and edge.relationship_type.upper() not in [r.upper() for r in relationship_filter]:
                    continue
                next_id = edge.target
                if next_id not in visited:
                    next_node = self.nodes.get(next_id)
                    step = {
                        "source": curr_node.name if curr_node else curr_id,
                        "source_type": curr_node.type if curr_node else "",
                        "relationship": edge.relationship_type,
                        "target": next_node.name if next_node else next_id,
                        "target_type": next_node.type if next_node else "",
                        "edge_id": edge.id,
                        "source_document": edge.source_document,
                        "source_chunk": edge.source_chunk or "",
                    }
                    new_visited = set(visited)
                    new_visited.add(next_id)
                    queue.append((next_id, path + [step], new_visited))

            # Traverse in edges (bidirectional traversal for semantic discovery)
            for eid in self.in_edges.get(curr_id, []):
                edge = self.edges.get(eid)
                if edge is None:
                    continue
                if relationship_filter and edge.relationship_type.upper() not in [r.upper() for r in relationship_filter]:
                    continue
                prev_id = edge.source
                if prev_id not in visited:
                    prev_node = self.nodes.get(prev_id)
                    step = {
                        "source": prev_node.name if prev_node else prev_id,
                        "source_type": prev_node.type if prev_node else "",
                        "relationship": f"INVERSE_{edge.relationship_type}",
                        "target": curr_node.name if curr_node else curr_id,
                        "target_type": curr_node.type if curr_node else "",
                        "edge_id": edge.id,
                        "source_document": edge.source_document,
                        "source_chunk": edge.source_chunk or "",
                    }
                    new_visited = set(visited)
                    new_visited.add(prev_id)
                    queue.append((prev_id, path + [step], new_visited))

        return results

    def execute_read_only_cypher(self, query: str) -> Dict[str, Any]:
        """
        Validates that the query is read-only and executes supported Cypher-like queries.
        Blocks mutating keywords: DELETE, DETACH, CREATE, SET, REMOVE, DROP, MERGE.
        """
        if len(query) > 2000:
            raise ValueError("Query exceeds the 2000 character limit.")
        if not re.match(r"^\s*MATCH\b", query, re.IGNORECASE) or not re.search(r"\bRETURN\b", query, re.IGNORECASE):
            raise ValueError("Only supported read-only MATCH ... RETURN queries are accepted.")
        if re.search(r";|//|/\*|\*/", query):
            raise ValueError("Multiple statements and comments are not allowed.")

        query_upper = query.upper()
        for kw in self.FORBIDDEN_CYPHER_KEYWORDS:
            if re.search(kw, query_upper):
                raise ValueError(f"Security Exception: Write/mutation keyword '{kw}' is strictly blocked in read-only Cypher query.")

        # Cypher evaluation
        # Match pattern: MATCH (n:Type {name: "..."})-[:REL]->(m) RETURN ...
        results = []

        # Example MATCH (p:Project)-[:USES]->(t:Technology)
        node_match = re.search(r"MATCH\s*\(([a-zA-Z0-9_]+)(?::([a-zA-Z0-9_]+))?(?:\s*\{\s*name\s*:\s*[\"']([^\"']+)[\"']\s*\})?\)", query, re.IGNORECASE)
        rel_match = re.search(r"-\[:([a-zA-Z0-9_]+)\]->\s*\(([a-zA-Z0-9_]+)(?::([a-zA-Z0-9_]+))?\)", query, re.IGNORECASE)

        if node_match and rel_match:
            src_type = node_match.group(2)
            src_name = node_match.group(3)
            rel_type = rel_match.group(1)
            tgt_type = rel_match.group(3)

            for eid, edge in self.edges.items():
                if edge.relationship_type.upper() == rel_type.upper():
                    s_node = self.nodes.get(edge.source)
                    t_node = self.nodes.get(edge.target)
                    if not s_node or not t_node:
                        continue
                    if src_type and s_node.type.lower() != src_type.lower():
                        continue
                    if src_name and s_node.name.lower() != src_name.lower():
                        continue
                    if tgt_type and t_node.type.lower() != tgt_type.lower():
                        continue
                    results.append({
                        "source": s_node.model_dump(),
                        "relationship": edge.relationship_type,
                        "target": t_node.model_dump(),
                        "confidence": edge.confidence,
                        "source_document": edge.source_document,
                    })
        elif node_match:
            src_type = node_match.group(2)
            src_name = node_match.group(3)
            for nid, node in self.nodes.items():
                if src_type and node.type.lower() != src_type.lower():
                    continue
                if src_name and node.name.lower() != src_name.lower():
                    continue
                results.append(node.model_dump())
        else:
            raise ValueError("Unsupported query shape. Use a node MATCH or a single directed relationship MATCH.")

        return {
            "query": query,
            "status": "success",
            "count": len(results),
            "results": results
        }
