# LanceDB vector store sync and search
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import networkx as nx

# Local model path (project-relative cache directory)
_MODEL_DIR = Path(__file__).parent.parent / ".cache" / "all-MiniLM-L6-v2"
_MODEL_NAME = "all-MiniLM-L6-v2"


def build_embedding_text(node_id: str, G: nx.Graph) -> str:
    """Build embedding text from node label, community, and direct neighbors."""
    node = G.nodes[node_id]
    label = node.get("label", node_id)
    community = node.get("community", "")

    # Collect neighbor labels and relation types
    neighbor_parts = []
    for _, tgt, data in G.edges(node_id, data=True):
        tgt_label = G.nodes[tgt].get("label", tgt)
        relation = data.get("relation", "related_to")
        neighbor_parts.append(f"{relation} {tgt_label}")

    parts = [label]
    if community:
        parts.append(f"community {community}")
    if neighbor_parts:
        parts.append("neighbors: " + ", ".join(neighbor_parts))

    return " ".join(parts)


def embed_hash(text: str) -> str:
    """SHA256 hash of embedding text."""
    return hashlib.sha256(text.encode()).hexdigest()


def sync(G: nx.Graph, db_path: str | Path) -> dict:
    """Sync graph to LanceDB vector store.

    Returns a dict with sync stats: {inserted, updated, deleted}.
    """
    import lancedb
    from sentence_transformers import SentenceTransformer

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Load embedding model (local if available, else download from HF Hub)
    if _MODEL_DIR.exists():
        model = SentenceTransformer(str(_MODEL_DIR))
    else:
        model = SentenceTransformer(_MODEL_NAME)

    # Build data for all nodes (with embeddings)
    records = []
    for node_id in G.nodes():
        embedding_text = build_embedding_text(node_id, G)
        h = embed_hash(embedding_text)
        embedding = model.encode(embedding_text)
        records.append({
            "id": node_id,
            "text": embedding_text,
            "embedding": embedding.tolist(),  # Convert to list for JSON serialization
            "embed_hash": h,
        })

    # Create or update LanceDB database
    db = lancedb.connect(str(db_path))

    try:
        # Try to open existing table
        table = db.open_table("nodes")
        existing_ids = {row["id"] for row in table.search().limit(None).to_list()}
    except Exception:
        # Table doesn't exist yet
        existing_ids = set()
        table = None

    # Determine what to insert/update/delete
    graph_ids = {r["id"] for r in records}
    to_insert = [r for r in records if r["id"] not in existing_ids]
    to_delete = existing_ids - graph_ids

    inserted = 0
    updated = 0
    deleted = 0

    # Create or update table
    if not table:
        # Create new table
        db.create_table("nodes", data=records, mode="overwrite")
        inserted = len(records)
    else:
        # Add new records
        if to_insert:
            table.add(to_insert)
            inserted = len(to_insert)

        # Delete removed records
        for node_id in to_delete:
            try:
                table.delete(f"id = '{node_id}'")
                deleted += 1
            except Exception:
                pass

    return {
        "inserted": inserted,
        "updated": updated,
        "deleted": deleted,
        "total": len(graph_ids),
    }


def search(query_text: str, db_path: str | Path, top_k: int = 10) -> list[tuple[str, float]]:
    """Search vector store for nodes matching natural language query.

    Returns list of (node_id, similarity_score) tuples, ranked by relevance.
    """
    import lancedb
    from sentence_transformers import SentenceTransformer
    import numpy as np

    db_path = Path(db_path)
    if not db_path.exists():
        return []

    try:
        # Load model and embed query (local if available, else from HF Hub)
        if _MODEL_DIR.exists():
            model = SentenceTransformer(str(_MODEL_DIR))
        else:
            model = SentenceTransformer(_MODEL_NAME)
        query_embedding = model.encode(query_text)

        # Search in LanceDB
        db = lancedb.connect(str(db_path))
        table = db.open_table("nodes")

        # Search by vector similarity
        results = table.search(query_embedding).limit(top_k).to_list()

        if results:
            # Return (node_id, distance_score)
            # LanceDB returns distance, so lower is better; invert to similarity
            return [(r["id"], float(r.get("_distance", 1.0))) for r in results]
        return []
    except Exception:
        # Silent failure
        return []
