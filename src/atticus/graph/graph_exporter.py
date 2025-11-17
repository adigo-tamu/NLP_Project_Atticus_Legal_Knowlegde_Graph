"""
Graph export utilities for various formats.

This module provides utilities to export the knowledge graph to standard formats
like GraphML, RDF/TTL, JSON, and others for interoperability.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from atticus.core.logger import get_logger
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class GraphExporter:
    """Export knowledge graph to various formats."""

    def __init__(self, neo4j_manager: Optional[Neo4jManager] = None):
        """
        Initialize graph exporter.

        Args:
            neo4j_manager: Neo4j manager instance
        """
        self.db = neo4j_manager or Neo4jManager()

    def export_to_graphml(
        self,
        output_path: str,
        document_id: Optional[str] = None,
        include_metadata: bool = True,
    ) -> bool:
        """
        Export graph to GraphML format.

        GraphML is an XML-based format for graphs, supported by many graph tools
        like Gephi, yEd, Cytoscape, etc.

        Args:
            output_path: Path to save GraphML file
            document_id: Optional document filter
            include_metadata: Whether to include all node/edge properties

        Returns:
            True if successful
        """
        logger.info(f"Exporting graph to GraphML: {output_path}")

        try:
            # Fetch nodes and edges
            nodes = self._fetch_nodes(document_id)
            edges = self._fetch_edges(document_id)

            logger.info(f"  Fetched {len(nodes)} nodes and {len(edges)} edges")

            # Create GraphML XML structure
            graphml = ET.Element(
                "graphml",
                xmlns="http://graphml.graphdrawing.org/xmlns",
                **{"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"},
            )

            # Define attributes (keys)
            if include_metadata:
                # Node attributes
                self._add_graphml_key(graphml, "id", "node", "string")
                self._add_graphml_key(graphml, "label", "node", "string")
                self._add_graphml_key(graphml, "type", "node", "string")
                self._add_graphml_key(graphml, "text", "node", "string")
                self._add_graphml_key(graphml, "confidence", "node", "double")
                self._add_graphml_key(graphml, "document_id", "node", "string")

                # Edge attributes
                self._add_graphml_key(graphml, "id", "edge", "string")
                self._add_graphml_key(graphml, "label", "edge", "string")
                self._add_graphml_key(graphml, "confidence", "edge", "double")
                self._add_graphml_key(graphml, "evidence", "edge", "string")

            # Create graph element
            graph = ET.SubElement(
                graphml,
                "graph",
                id="KnowledgeGraph",
                edgedefault="directed",
            )

            # Add nodes
            for node in nodes:
                node_elem = ET.SubElement(graph, "node", id=str(node["id"]))

                if include_metadata:
                    self._add_graphml_data(node_elem, "id", node.get("id", ""))
                    self._add_graphml_data(node_elem, "label", node.get("labels", ["Unknown"])[0])
                    self._add_graphml_data(node_elem, "type", node.get("type", ""))
                    self._add_graphml_data(node_elem, "text", node.get("text", "")[:100])  # Truncate
                    self._add_graphml_data(node_elem, "confidence", node.get("confidence", 0.0))
                    self._add_graphml_data(node_elem, "document_id", node.get("document_id", ""))

            # Add edges
            for i, edge in enumerate(edges):
                edge_elem = ET.SubElement(
                    graph,
                    "edge",
                    id=f"e{i}",
                    source=str(edge["source"]),
                    target=str(edge["target"]),
                )

                if include_metadata:
                    self._add_graphml_data(edge_elem, "id", edge.get("id", ""))
                    self._add_graphml_data(edge_elem, "label", edge.get("type", ""))
                    self._add_graphml_data(edge_elem, "confidence", edge.get("confidence", 0.0))
                    self._add_graphml_data(edge_elem, "evidence", edge.get("evidence", "")[:200])

            # Write to file
            tree = ET.ElementTree(graphml)
            ET.indent(tree, space="  ")  # Pretty print
            tree.write(output_path, encoding="utf-8", xml_declaration=True)

            logger.info(f"✓ Exported {len(nodes)} nodes and {len(edges)} edges to GraphML")
            return True

        except Exception as e:
            logger.error(f"Failed to export to GraphML: {e}")
            return False

    def export_to_rdf(
        self,
        output_path: str,
        document_id: Optional[str] = None,
        format: str = "turtle",
        namespace: str = "http://atticus.legal/",
    ) -> bool:
        """
        Export graph to RDF format (Turtle, N-Triples, or RDF/XML).

        Args:
            output_path: Path to save RDF file
            document_id: Optional document filter
            format: RDF format ('turtle', 'ntriples', 'rdfxml')
            namespace: Base namespace for URIs

        Returns:
            True if successful
        """
        logger.info(f"Exporting graph to RDF ({format}): {output_path}")

        try:
            # Fetch nodes and edges
            nodes = self._fetch_nodes(document_id)
            edges = self._fetch_edges(document_id)

            logger.info(f"  Fetched {len(nodes)} nodes and {len(edges)} edges")

            # Generate RDF triples
            triples = []

            # Namespace prefixes
            prefixes = {
                "@prefix": "atticus:",
                "@base": namespace,
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
            }

            if format == "turtle":
                # Write Turtle format
                lines = []

                # Prefixes
                for prefix, uri in prefixes.items():
                    if prefix != "@base":
                        lines.append(f"@prefix {prefix} <{uri}> .")
                lines.append(f"@base <{namespace}> .")
                lines.append("")

                # Node triples
                for node in nodes:
                    node_uri = f"<entity/{self._sanitize_uri(node['id'])}>"
                    node_type = node.get("labels", ["Entity"])[0]

                    lines.append(f"{node_uri}")
                    lines.append(f"  rdf:type atticus:{node_type} ;")
                    lines.append(f"  rdfs:label \"{self._escape_literal(node.get('text', '')[:100])}\" ;")
                    lines.append(f"  atticus:confidence \"{node.get('confidence', 0.0)}\"^^xsd:double ;")

                    if node.get("type"):
                        lines.append(f"  atticus:entityType \"{node['type']}\" ;")

                    if node.get("document_id"):
                        lines.append(f"  atticus:documentId \"{node['document_id']}\" ;")

                    lines.append("  .")
                    lines.append("")

                # Edge triples
                for edge in edges:
                    source_uri = f"<entity/{self._sanitize_uri(edge['source'])}>"
                    target_uri = f"<entity/{self._sanitize_uri(edge['target'])}>"
                    rel_type = edge.get("type", "REFERENCES")

                    lines.append(f"{source_uri}")
                    lines.append(f"  atticus:{rel_type} {target_uri} ;")

                    # Edge as blank node with properties
                    if edge.get("confidence") or edge.get("evidence"):
                        edge_uri = f"<relationship/{self._sanitize_uri(edge.get('id', ''))}>"
                        lines.append(f"  atticus:hasRelationship {edge_uri} .")
                        lines.append(f"{edge_uri}")
                        lines.append(f"  rdf:type atticus:Relationship ;")
                        lines.append(f"  atticus:target {target_uri} ;")

                        if edge.get("confidence"):
                            lines.append(f"  atticus:confidence \"{edge['confidence']}\"^^xsd:double ;")

                        if edge.get("evidence"):
                            evidence = self._escape_literal(edge["evidence"][:200])
                            lines.append(f"  atticus:evidence \"{evidence}\" ;")

                        lines.append("  .")

                    lines.append("")

                # Write to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

            elif format == "ntriples":
                # Write N-Triples format (simpler)
                lines = []

                for node in nodes:
                    node_uri = f"<{namespace}entity/{self._sanitize_uri(node['id'])}>"
                    node_type = node.get("labels", ["Entity"])[0]

                    lines.append(
                        f"{node_uri} <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
                        f"<{namespace}{node_type}> ."
                    )

                    if node.get("text"):
                        text = self._escape_literal(node["text"][:100])
                        lines.append(
                            f"{node_uri} <http://www.w3.org/2000/01/rdf-schema#label> "
                            f'"{text}" .'
                        )

                for edge in edges:
                    source_uri = f"<{namespace}entity/{self._sanitize_uri(edge['source'])}>"
                    target_uri = f"<{namespace}entity/{self._sanitize_uri(edge['target'])}>"
                    rel_type = edge.get("type", "REFERENCES")

                    lines.append(
                        f"{source_uri} <{namespace}{rel_type}> {target_uri} ."
                    )

                # Write to file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

            else:
                logger.error(f"Unsupported RDF format: {format}")
                return False

            logger.info(f"✓ Exported {len(nodes)} nodes and {len(edges)} edges to RDF")
            return True

        except Exception as e:
            logger.error(f"Failed to export to RDF: {e}")
            return False

    def export_to_json(
        self,
        output_path: str,
        document_id: Optional[str] = None,
        pretty: bool = True,
    ) -> bool:
        """
        Export graph to JSON format.

        Args:
            output_path: Path to save JSON file
            document_id: Optional document filter
            pretty: Whether to pretty-print JSON

        Returns:
            True if successful
        """
        logger.info(f"Exporting graph to JSON: {output_path}")

        try:
            # Fetch nodes and edges
            nodes = self._fetch_nodes(document_id)
            edges = self._fetch_edges(document_id)

            logger.info(f"  Fetched {len(nodes)} nodes and {len(edges)} edges")

            # Build JSON structure
            graph_data = {
                "metadata": {
                    "document_id": document_id,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                },
                "nodes": nodes,
                "edges": edges,
            }

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                if pretty:
                    json.dump(graph_data, f, indent=2, ensure_ascii=False, default=str)
                else:
                    json.dump(graph_data, f, ensure_ascii=False, default=str)

            logger.info(f"✓ Exported {len(nodes)} nodes and {len(edges)} edges to JSON")
            return True

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return False

    def export_to_cypher(
        self,
        output_path: str,
        document_id: Optional[str] = None,
    ) -> bool:
        """
        Export graph to Cypher CREATE statements.

        Useful for recreating the graph in another Neo4j instance.

        Args:
            output_path: Path to save Cypher file
            document_id: Optional document filter

        Returns:
            True if successful
        """
        logger.info(f"Exporting graph to Cypher: {output_path}")

        try:
            # Fetch nodes and edges
            nodes = self._fetch_nodes(document_id)
            edges = self._fetch_edges(document_id)

            logger.info(f"  Fetched {len(nodes)} nodes and {len(edges)} edges")

            lines = []

            # Header
            lines.append("// Knowledge Graph Export - Cypher Statements")
            lines.append(f"// Generated for document_id: {document_id or 'ALL'}")
            lines.append(f"// Nodes: {len(nodes)}, Edges: {len(edges)}")
            lines.append("")

            # Create nodes
            lines.append("// Create Nodes")
            for node in nodes:
                labels = ":".join(node.get("labels", ["Entity"]))
                properties = self._dict_to_cypher_props(node)
                lines.append(f"CREATE (:{labels} {properties});")

            lines.append("")

            # Create relationships
            lines.append("// Create Relationships")
            for edge in edges:
                source_id = edge["source"]
                target_id = edge["target"]
                rel_type = edge.get("type", "REFERENCES")
                properties = self._dict_to_cypher_props(edge, exclude=["source", "target", "type"])

                lines.append(
                    f"MATCH (source {{id: '{source_id}'}}), (target {{id: '{target_id}'}})\n"
                    f"CREATE (source)-[:{rel_type} {properties}]->(target);"
                )

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(f"✓ Exported {len(nodes)} nodes and {len(edges)} edges to Cypher")
            return True

        except Exception as e:
            logger.error(f"Failed to export to Cypher: {e}")
            return False

    def _fetch_nodes(self, document_id: Optional[str] = None) -> List[Dict]:
        """Fetch all nodes from Neo4j."""
        if document_id:
            query = """
            MATCH (n {document_id: $document_id})
            RETURN n.id as id, labels(n) as labels, properties(n) as properties
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (n)
            RETURN n.id as id, labels(n) as labels, properties(n) as properties
            """
            params = {}

        result = self.db.execute_query(query, params)

        nodes = []
        for record in result:
            node = dict(record["properties"])
            node["id"] = record["id"]
            node["labels"] = record["labels"]
            nodes.append(node)

        return nodes

    def _fetch_edges(self, document_id: Optional[str] = None) -> List[Dict]:
        """Fetch all edges from Neo4j."""
        if document_id:
            query = """
            MATCH (source)-[r {document_id: $document_id}]->(target)
            RETURN source.id as source, target.id as target, type(r) as type, properties(r) as properties
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (source)-[r]->(target)
            RETURN source.id as source, target.id as target, type(r) as type, properties(r) as properties
            """
            params = {}

        result = self.db.execute_query(query, params)

        edges = []
        for record in result:
            edge = dict(record["properties"])
            edge["source"] = record["source"]
            edge["target"] = record["target"]
            edge["type"] = record["type"]
            edges.append(edge)

        return edges

    def _add_graphml_key(self, parent: ET.Element, name: str, for_type: str, attr_type: str):
        """Add GraphML key definition."""
        ET.SubElement(
            parent,
            "key",
            id=name,
            **{"for": for_type, "attr.name": name, "attr.type": attr_type},
        )

    def _add_graphml_data(self, parent: ET.Element, key: str, value):
        """Add GraphML data element."""
        if value is not None:
            data = ET.SubElement(parent, "data", key=key)
            data.text = str(value)

    def _sanitize_uri(self, text: str) -> str:
        """Sanitize text for use in URIs."""
        import re

        # Remove special characters, keep alphanumeric and hyphens
        return re.sub(r"[^a-zA-Z0-9_-]", "_", text)

    def _escape_literal(self, text: str) -> str:
        """Escape text for use in RDF literals."""
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def _dict_to_cypher_props(self, props: Dict, exclude: Optional[List[str]] = None) -> str:
        """Convert dictionary to Cypher properties string."""
        exclude = exclude or []
        filtered = {k: v for k, v in props.items() if k not in exclude}

        if not filtered:
            return "{}"

        prop_strs = []
        for key, value in filtered.items():
            if isinstance(value, str):
                prop_strs.append(f"{key}: '{value.replace(chr(39), chr(39)+chr(39))}'")  # Escape quotes
            elif isinstance(value, (int, float)):
                prop_strs.append(f"{key}: {value}")
            elif isinstance(value, bool):
                prop_strs.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, list):
                # Convert list to string representation
                prop_strs.append(f"{key}: {json.dumps(value)}")
            else:
                prop_strs.append(f"{key}: '{str(value)}'")

        return "{" + ", ".join(prop_strs) + "}"
