#!/usr/bin/env python
"""code-knowledge: code-only knowledge graph with vector search"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Optional
import argparse
import networkx as nx

from . import detect, extract, cache, build, cluster, export, vector


# Output directory: code-knowledge-out/ in the current working directory
# (can be overridden with --out flag)
DEFAULT_OUT_DIR = Path.cwd() / "code-knowledge-out"


def cmd_update(root: Path, out_dir: Path = DEFAULT_OUT_DIR) -> None:
    """Full pipeline: detect → extract → build → cluster → export → sync_vectors"""
    root = root.resolve()
    out_dir = out_dir.resolve()

    print(f"[code-knowledge] Scanning {root}")
    detection = detect.detect(root)
    files = detection["files"]
    print(f"[code-knowledge] Found {detection['total_files']} code files")

    print(f"[code-knowledge] Extracting...")
    manifest_path = out_dir / "manifest.json"
    extractions = []
    for fpath in files:
        p = Path(fpath)
        # Check cache first
        cached = cache.load_cached(p, out_dir)
        if cached:
            extractions.append(cached)
            continue
        # Extract
        result = extract.extract([p], cache_root=out_dir)
        if result.get("nodes") or result.get("edges"):
            cache.save_cached(p, result, out_dir)
            extractions.append(result)

    print(f"[code-knowledge] Building graph...")
    G = build.build(extractions, directed=True)
    print(f"[code-knowledge] Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print(f"[code-knowledge] Clustering...")
    communities = cluster.cluster(G)
    for cid, nodes in communities.items():
        for node_id in nodes:
            G.nodes[node_id]["community"] = cid
    print(f"[code-knowledge] {len(communities)} communities detected")

    print(f"[code-knowledge] Exporting...")
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_path = out_dir / "graph.json"
    export.to_json(G, communities, str(graph_path))
    print(f"[code-knowledge] Wrote {graph_path}")

    print(f"[code-knowledge] Syncing vector store...")
    vector_dir = out_dir / "vectors"
    sync_result = vector.sync(G, vector_dir)
    print(f"[code-knowledge] {sync_result}")

    # Save manifest
    detect.save_manifest(files, str(manifest_path))
    print(f"[code-knowledge] Done")


def cmd_index(graph_path: Path = DEFAULT_OUT_DIR / "graph.json") -> None:
    """Rebuild vector store from existing graph.json"""
    graph_path = Path(graph_path)
    if not graph_path.exists():
        print(f"[code-knowledge] ERROR: {graph_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"[code-knowledge] Loading graph from {graph_path}")
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    G = nx.node_link_graph(data, edges="links", directed=True)
    print(f"[code-knowledge] Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print(f"[code-knowledge] Syncing vector store...")
    vector_dir = graph_path.parent / "vectors"
    sync_result = vector.sync(G, vector_dir)
    print(f"[code-knowledge] {sync_result}")


def _build_relationship_chains(G: nx.Graph, start_node_id: str, max_depth: int = 2, max_chains: int = 5) -> dict:
    """Build relationship chains from a node using BFS.

    Returns a dict with 'calls' and 'called_by' lists:
    {
        'calls': ["validates → token", "imports → logger"],
        'called_by': ["main → calls", "handler → uses"]
    }
    """
    calls = []
    called_by = []

    # Outgoing edges (what this node calls/uses/imports)
    for _, neighbor, data in G.out_edges(start_node_id, data=True):
        relation = data.get('relation', 'related_to')
        neighbor_label = G.nodes[neighbor].get('label', neighbor)
        calls.append(f"{relation} → {neighbor_label}")

    # Incoming edges (what calls/uses/imports this node)
    for source, _, data in G.in_edges(start_node_id, data=True):
        relation = data.get('relation', 'related_to')
        source_label = G.nodes[source].get('label', source)
        called_by.append(f"{source_label} → {relation}")

    return {
        'calls': calls[:max_chains],
        'called_by': called_by[:max_chains]
    }


def cmd_query(query_text: str, db_path: Path = DEFAULT_OUT_DIR / "vectors", top_k: int = 10, graph_path: Path = DEFAULT_OUT_DIR / "graph.json") -> None:
    """Natural language query → vector search → show relationship chains"""
    db_path = Path(db_path)
    graph_path = Path(graph_path)

    if not db_path.exists():
        print(f"[code-knowledge] ERROR: vector store not found at {db_path}", file=sys.stderr)
        sys.exit(1)
    if not graph_path.exists():
        print(f"[code-knowledge] ERROR: graph not found at {graph_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[code-knowledge] Querying: {query_text}")
    results = vector.search(query_text, db_path, top_k=top_k)

    if not results:
        print("[code-knowledge] No results found")
        return

    # Load graph for relationship chain expansion
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    G = nx.node_link_graph(data, edges="links", directed=True)

    print(f"\n[code-knowledge] Top {len(results)} results with relationship chains:\n")
    for idx, (node_id, score) in enumerate(results, 1):
        node = G.nodes[node_id]
        print(f"{idx}. {node.get('label', node_id)} (relevance: {score:.3f})")
        print(f"   📄 File: {node.get('source_file')}")
        print(f"   📍 Location: {node.get('source_location')}")
        print(f"   👥 Community: {node.get('community')}")

        # Show relationship chains (what it calls, what calls it)
        chains = _build_relationship_chains(G, node_id, max_chains=5)

        if chains['calls']:
            print(f"   ➡️  This node:")
            for chain in chains['calls'][:3]:
                print(f"      {chain}")

        if chains['called_by']:
            print(f"   ⬅️  Called/used by:")
            for chain in chains['called_by'][:3]:
                print(f"      {chain}")

        print()


def cmd_path(label_a: str, label_b: str, graph_path: Path = DEFAULT_OUT_DIR / "graph.json") -> None:
    """Shortest path between two node labels"""
    graph_path = Path(graph_path)
    if not graph_path.exists():
        print(f"[code-knowledge] ERROR: graph not found at {graph_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    G = nx.node_link_graph(data, edges="links", directed=True)

    # Find nodes by label
    node_a_id = None
    node_b_id = None
    for nid, ndata in G.nodes(data=True):
        if ndata.get("label") == label_a:
            node_a_id = nid
        if ndata.get("label") == label_b:
            node_b_id = nid

    if not node_a_id or not node_b_id:
        print(f"[code-knowledge] ERROR: could not find nodes for '{label_a}' and '{label_b}'", file=sys.stderr)
        sys.exit(1)

    try:
        path = nx.shortest_path(G, node_a_id, node_b_id)
        print(f"[code-knowledge] Path ({len(path)} nodes):")
        for nid in path:
            print(f"  {G.nodes[nid].get('label', nid)}")
    except nx.NetworkXNoPath:
        print(f"[code-knowledge] No path found between '{label_a}' and '{label_b}'")


def cmd_explain(label: str, graph_path: Path = DEFAULT_OUT_DIR / "graph.json") -> None:
    """Node metadata and neighbors"""
    graph_path = Path(graph_path)
    if not graph_path.exists():
        print(f"[code-knowledge] ERROR: graph not found at {graph_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    G = nx.node_link_graph(data, edges="links", directed=True)

    # Find node by label
    node_id = None
    for nid, ndata in G.nodes(data=True):
        if ndata.get("label") == label:
            node_id = nid
            break

    if not node_id:
        print(f"[code-knowledge] ERROR: node '{label}' not found", file=sys.stderr)
        sys.exit(1)

    node = G.nodes[node_id]
    print(f"[code-knowledge] {label}")
    print(f"  ID: {node_id}")
    print(f"  File: {node.get('source_file')}")
    print(f"  Location: {node.get('source_location')}")
    print(f"  Community: {node.get('community')}")
    print(f"  Contributor: {node.get('contributor', 'unknown')}")

    # Outgoing edges
    out_edges = list(G.out_edges(node_id, data=True))
    if out_edges:
        print(f"\n  Calls/references ({len(out_edges)}):")
        for _, tgt, data in out_edges[:10]:
            rel = data.get("relation", "related_to")
            tgt_label = G.nodes[tgt].get("label", tgt)
            print(f"    {rel} → {tgt_label}")

    # Incoming edges
    in_edges = list(G.in_edges(node_id, data=True))
    if in_edges:
        print(f"\n  Called by ({len(in_edges)}):")
        for src, _, data in in_edges[:10]:
            rel = data.get("relation", "related_to")
            src_label = G.nodes[src].get("label", src)
            print(f"    {src_label} → {rel}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="code-knowledge: code-only knowledge graph with vector search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # update
    update_parser = subparsers.add_parser("update", help="Full pipeline: detect → extract → build → cluster → export → sync")
    update_parser.add_argument("path", nargs="?", default=".", help="Root directory to scan")
    update_parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory (default: ./code-knowledge-out)")

    # index
    index_parser = subparsers.add_parser("index", help="Rebuild vector store from graph.json")
    index_parser.add_argument("--graph", default=str(DEFAULT_OUT_DIR / "graph.json"), help="Path to graph.json")

    # query
    query_parser = subparsers.add_parser("query", help="Natural language query")
    query_parser.add_argument("text", help="Query text")
    query_parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    query_parser.add_argument("--graph", default=str(DEFAULT_OUT_DIR / "graph.json"), help="Path to graph.json")

    # path
    path_parser = subparsers.add_parser("path", help="Shortest path between nodes")
    path_parser.add_argument("a", help="First node label")
    path_parser.add_argument("b", help="Second node label")
    path_parser.add_argument("--graph", default=str(DEFAULT_OUT_DIR / "graph.json"), help="Path to graph.json")

    # explain
    explain_parser = subparsers.add_parser("explain", help="Show node details and neighbors")
    explain_parser.add_argument("label", help="Node label")
    explain_parser.add_argument("--graph", default=str(DEFAULT_OUT_DIR / "graph.json"), help="Path to graph.json")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "update":
            cmd_update(Path(args.path), Path(args.out))
        elif args.command == "index":
            cmd_index(Path(args.graph))
        elif args.command == "query":
            cmd_query(args.text, top_k=args.top_k, graph_path=Path(args.graph))
        elif args.command == "path":
            cmd_path(args.a, args.b, Path(args.graph))
        elif args.command == "explain":
            cmd_explain(args.label, Path(args.graph))
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"[code-knowledge] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
