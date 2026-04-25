# export graph to JSON
from __future__ import annotations
import json
import re
from pathlib import Path
import networkx as nx
from networkx.readwrite import json_graph


def _node_community_map(communities: dict[int, list[str]]) -> dict[str, int]:
    """Map node ID → community ID."""
    node_to_community = {}
    for cid, nodes in communities.items():
        for node_id in nodes:
            node_to_community[node_id] = cid
    return node_to_community


def _strip_diacritics(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED": 1.0, "INFERRED": 0.5, "AMBIGUOUS": 0.2}


def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str, *, force: bool = False) -> None:
    """Export graph to JSON with minimal schema: id, label, source_file, source_location, contributor, community for nodes; from, to, relation for edges."""
    # Safety check: refuse to silently shrink an existing graph
    existing_path = Path(output_path)
    if not force and existing_path.exists():
        try:
            existing_data = json.loads(existing_path.read_text(encoding="utf-8"))
            existing_n = len(existing_data.get("nodes", []))
            new_n = G.number_of_nodes()
            if new_n < existing_n:
                import sys as _sys
                print(
                    f"[code-knowledge] WARNING: new graph has {new_n} nodes but existing "
                    f"graph.json has {existing_n}. Refusing to overwrite — you may be "
                    f"missing files from a previous session. Pass force=True to override.",
                    file=_sys.stderr,
                )
                return
        except Exception:
            pass

    node_community = _node_community_map(communities)
    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)

    # Simplify node output to required fields only
    simplified_nodes = []
    for node in data["nodes"]:
        simplified_nodes.append({
            "id": node["id"],
            "label": node.get("label", node["id"]),
            "source_file": node.get("source_file"),
            "source_location": node.get("source_location"),
            "contributor": node.get("contributor"),
            "community": node_community.get(node["id"]),
        })
    data["nodes"] = simplified_nodes

    # Simplify edge output to required fields only
    # Keep "source"/"target" for NetworkX compatibility
    simplified_links = []
    for link in data["links"]:
        simplified_links.append({
            "source": link["source"],
            "target": link["target"],
            "relation": link.get("relation", "related_to"),
        })
    data["links"] = simplified_links

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def prune_dangling_edges(graph_data: dict) -> tuple[dict, int]:
    """Remove edges whose source or target node is not in the node set.

    Returns the cleaned graph_data dict and the number of pruned edges.
    """
    node_ids = {n["id"] for n in graph_data["nodes"]}
    links_key = "links" if "links" in graph_data else "edges"
    before = len(graph_data[links_key])
    graph_data[links_key] = [
        e for e in graph_data[links_key]
        if e.get("source") in node_ids and e.get("target") in node_ids
    ]
    return graph_data, before - len(graph_data[links_key])
