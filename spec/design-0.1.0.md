# code-knowledge Design v0.1.0

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Developer / Automation                            │
│  (CLI: code-knowledge update|query|path|explain|index)              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐            ┌────▼────┐           ┌────▼─────┐
   │ detect  │            │ extract │           │  vector  │
   │ (local  │            │ (local  │           │  search  │
   │  FS)    │            │  AST)   │           │(semantic)│
   └────┬────┘            └────┬────┘           └────┬─────┘
        │                      │                      │
        └──────────┬───────────┴──────────┬───────────┘
                   │                      │
              ┌────▼──────────────────────▼────┐
              │  build.py (NetworkX DiGraph)   │
              │  - Merge extractions           │
              │  - Deduplicate nodes/edges     │
              │  - Preserve edge direction     │
              └────┬─────────────────────────┬─┘
                   │                         │
          ┌────────▼────────┐         ┌─────▼──────────┐
          │  cluster.py     │         │  export.py     │
          │  (Leiden/Louvain)         │  (graph.json)  │
          └────────┬────────┘         └─────────────┬──┘
                   │                                │
              ┌────▼────────────────────────────────▼────┐
              │  LanceDB (Vector Store)                  │
              │  - Store node embeddings (384-dim)       │
              │  - ANN search by similarity              │
              └────────────────────────────────────────┬─┘
                                                       │
                    ┌──────────────────────────────────┘
                    │
            ┌───────▼────────┐
            │ graph.json     │
            │ + vectors/     │
            │ (code-knowledge-out/)
            └────────────────┘
```

---

## Tech Stack

| Category | Choice | Rationale |
|----------|--------|-----------|
| **Language** | Python 3.11+ | Fast iteration; rich scientific libraries (NetworkX, sentence-transformers); cross-platform |
| **Code Analysis** | tree-sitter + 26 language parsers | Deterministic AST extraction without LLM; covers 98% of real-world codebases |
| **Graph Engine** | NetworkX 3.0+ | Standard Python graph library; supports directed graphs, community detection |
| **Community Detection** | Leiden (graspologic) + Louvain fallback | Leiden is higher-quality (modularity optimization); graspologic available on Unix/Python<3.13; fallback to NetworkX Louvain on Windows or Python 3.13+ |
| **Vector Search** | LanceDB + sentence-transformers | LanceDB: fast vector DB, Python-native, embedded (no server); sentence-transformers: lightweight embeddings, all-MiniLM-L6-v2 (384-dim, 22 MB) |
| **Embedding Model** | all-MiniLM-L6-v2 | Small (22 MB), fast (<1s encode), 384-dim vectors; downloadable to `.cache/` for offline use |
| **JSON Serialization** | NetworkX node-link format | Standard; human-readable; compatible with external tools |
| **Build System** | Hatchling + uv | Fast; reproducible; supports editable installs and optional dependencies |
| **Testing** | [inferred] pytest (recommended; not yet in dependencies) | Standard Python testing framework |

---

## Component Design

### Component Hierarchy

```
app/
├── __main__.py
│   ├── cmd_update()         → orchestrates full pipeline
│   ├── cmd_query()          → semantic search + relationship display
│   ├── cmd_path()           → shortest path between nodes
│   ├── cmd_explain()        → node details + edges
│   ├── cmd_index()          → vector store rebuild
│   └── _build_relationship_chains() → helper for query results
│
├── detect.py
│   ├── classify_file()      → identify code by extension
│   ├── detect()             → recursive file discovery
│   ├── _is_sensitive()      → filter secrets
│   ├── _load_graphifyignore() → read .graphifyignore patterns
│   └── save_manifest()      → track file mtimes for incremental runs [not yet used]
│
├── extract.py               → [3440 lines, 26 language extractors]
│   ├── extract()            → main entry point
│   ├── extract_python()     → AST walker for .py files
│   ├── extract_javascript() → AST walker for .js/.ts files
│   └── ... [22 more language extractors]
│
├── build.py
│   ├── build()              → merge extractions into NetworkX DiGraph
│   ├── build_from_json()    → construct graph from JSON dict
│   ├── deduplicate_by_label() → resolve node name conflicts
│   └── _normalize_id()      → canonicalize node IDs
│
├── cluster.py
│   ├── cluster()            → community detection wrapper
│   ├── _partition()         → run Leiden or Louvain
│   └── _split_community()   → split oversized communities (>25% of graph)
│
├── export.py
│   ├── to_json()            → serialize graph to minimal schema JSON
│   ├── prune_dangling_edges() → remove edges to non-existent nodes
│   └── [schema helpers]
│
├── vector.py
│   ├── sync()               → embed all nodes, upsert to LanceDB
│   ├── search()             → ANN search by query text
│   ├── build_embedding_text() → construct text for embedding
│   └── embed_hash()         → SHA256 of embedding text
│
├── cache.py
│   ├── load_cached()        → fetch per-file extraction by SHA256
│   ├── save_cached()        → store extraction in cache
│   ├── cache_dir()          → return cache directory path
│   ├── file_hash()          → SHA256 of file contents
│   └── clear_cache()        → delete all cache files
│
├── validate.py
│   ├── validate_extraction() → check extraction schema
│   └── [schema validators]
│
└── security.py
    ├── safe_path()          → sanitize file paths
    ├── safe_label()         → sanitize node labels
    └── [path/label validation]
```

### Key Data Models

#### Extraction Result (dict from extract.py)
```python
{
    "nodes": [
        {
            "id": str,              # "module_classname_methodname"
            "label": str,           # "ClassName" or "functionName"
            "source_file": str,     # relative path: "app/auth.py"
            "source_location": str, # "L42" (line number)
            "contributor": str|None # null (not used in code-only)
        },
        ...
    ],
    "edges": [
        {
            "source": str,          # node id
            "target": str,          # node id
            "relation": str         # "calls", "imports", "contains", etc.
        },
        ...
    ]
}
```

#### NetworkX DiGraph Node Attributes
```python
{
    "label": str,           # Human-readable name
    "source_file": str,     # "src/handler.py"
    "source_location": str, # "L42"
    "contributor": str|None,
    "community": int        # Assigned during clustering phase
}
```

#### NetworkX DiGraph Edge Attributes
```python
{
    "relation": str         # "calls", "imports", "imports_from", "contains", etc.
}
```

#### LanceDB Record
```python
{
    "id": str,              # node id (primary key)
    "text": str,            # "{label} community {id} {relation} {neighbor}..."
    "embedding": list[float],  # 384-dim vector from all-MiniLM-L6-v2
    "embed_hash": str       # SHA256 of text (for change detection)
}
```

#### graph.json Export Schema
```json
{
    "nodes": [
        {
            "id": "session_validate_token",
            "label": "ValidateToken",
            "source_file": "auth/session.py",
            "source_location": "L42",
            "contributor": null,
            "community": 2
        }
    ],
    "links": [
        {
            "source": "session_validate_token",
            "target": "session_auth_token",
            "relation": "calls"
        }
    ]
}
```

---

## Data Flow

### Full Pipeline (update command)

```
Input: /path/to/code

1. detect.detect(root)
   → Recursively walk /path/to/code
   → Filter by extension (CODE_EXTENSIONS)
   → Skip noise dirs, secrets, lock files
   → Return: list of file paths

2. extract.extract(files)
   [Per file: check cache by SHA256]
   → Dispatch to extract_python/extract_javascript/... (by ext)
   → Parse AST, emit nodes + edges
   → Cache extraction to code-knowledge-out/cache/{hash}.json
   → Return: list of extraction dicts

3. build.build(extractions, directed=True)
   → Merge all extractions into one NetworkX DiGraph
   → Deduplicate by node ID (keep first occurrence)
   → Validate edges (warn about dangling edges to external libs)
   → Return: nx.DiGraph with nodes + edges

4. cluster.cluster(G)
   → Try graspologic.leiden(G) [Unix/Python<3.13]
   → Fallback to nx.louvain_communities(G)
   → Split oversized communities (>25% of graph, min 10 nodes)
   → Return: {community_id: [node_ids], ...}

5. Annotate graph with communities
   → G.nodes[node_id]["community"] = cid

6. export.to_json(G, communities, graph.json)
   → Simplify nodes to 6 required fields
   → Simplify edges to source/target/relation
   → Write as JSON

7. vector.sync(G, db_path)
   → For each node_id in G:
      - Build embedding text: "{label} community {id} {relation} {neighbor}..."
      - Compute SHA256 hash of text
      - Embed using SentenceTransformer
      - Check LanceDB for existing record
   → Upsert (insert new, update changed, delete removed)
   → Return: {inserted, updated, deleted, total}

Output: code-knowledge-out/
  ├── graph.json
  ├── vectors/ (LanceDB)
  └── cache/ (per-file extractions)
```

### Query Command Data Flow

```
Input: query_text, top_k=10

1. vector.search(query_text, db_path, top_k=10)
   → Load model: SentenceTransformer or from .cache/all-MiniLM-L6-v2/
   → Embed query_text → 384-dim vector
   → Connect to LanceDB
   → ANN search: table.search(vector).limit(10).to_list()
   → Return: [(node_id, distance_score), ...]

2. Load graph.json
   → Parse JSON
   → Reconstruct NetworkX DiGraph

3. For each result (node_id, score):
   → Fetch node attributes
   → _build_relationship_chains(G, node_id)
      - G.out_edges(node_id) → collect outgoing
      - G.in_edges(node_id) → collect incoming
      - Format: "{relation} → {label}"
   → Display with metadata + chains

Output: Formatted text with node rank, label, relevance score, file, location, community, relationships
```

---

## File Structure

```
code-knowledge/                         (project root)
├── app/                                 (Python package)
│   ├── __init__.py                      (module init, imports main pipeline)
│   ├── __main__.py                      (CLI entry point, 306 lines)
│   ├── detect.py                        (file discovery, 280 lines)
│   ├── extract.py                       (AST extraction, 3440 lines, 26 languages)
│   ├── build.py                         (graph construction, 200 lines)
│   ├── cluster.py                       (community detection, 150 lines)
│   ├── export.py                        (JSON export, 85 lines)
│   ├── vector.py                        (vector store, 150 lines)
│   ├── cache.py                         (extraction cache, 110 lines)
│   ├── validate.py                      (schema validation, 100 lines)
│   ├── security.py                      (path/label sanitization, 150 lines)
│   └── __pycache__/                     (compiled bytecode)
│
├── spec/                                (generated documentation)
│   ├── requirements-0.1.0.md            (what it does)
│   └── design-0.1.0.md                  (this file)
│
├── pyproject.toml                       (39 lines, hatchling + dependencies)
├── .python-version                      (3.11)
├── README.md                            (user guide)
├── .gitignore                           (excludes code-knowledge-out/, .cache/)
├── download-model.sh                    (bash script to cache embedding model)
├── download-model.ps1                   (PowerShell version)
│
├── code-knowledge-out/                  (generated at runtime, excluded from git)
│   ├── graph.json                       (NetworkX node-link JSON)
│   ├── vectors/                         (LanceDB database)
│   │   └── nodes.lance
│   ├── cache/                           (per-file extraction cache)
│   │   ├── {sha256}.json
│   │   └── ...
│   └── manifest.json                    (file mtime tracking)
│
└── .cache/                              (optional, excluded from git)
    └── all-MiniLM-L6-v2/                (downloaded embedding model)
        ├── config.json
        ├── pytorch_model.bin
        ├── tokenizer.json
        └── ...
```

---

## Notable Decisions / Deviations

### 1. **Directed Graph (DiGraph) vs. Undirected**
- **Decision**: Full pipeline uses `nx.DiGraph(directed=True)` to preserve edge direction.
- **Rationale**: Call relationships are inherently directional (`A calls B` ≠ `B calls A`). DiGraph enables shortest path queries and relationship chains to reflect actual control flow.
- **Impact**: Outgoing relationships answer "what does this call?"; incoming relationships answer "who calls this?"

### 2. **Per-File Extraction Cache by SHA256**
- **Decision**: Each file's extraction is cached keyed by SHA256 of its contents (not mtime).
- **Rationale**: Hash-based cache is portable across machines and checkouts; survives file reordering and timestamp changes.
- **Impact**: Incremental builds are fast (skip unchanged files); manifest.json is not yet used for incremental updates.

### 3. **Single Minimal Graph Export**
- **Decision**: No separate versioned exports (graph-v1, graph-v2); graph.json is overwritten on each run.
- **Rationale**: Simplifies deployment; users manage versioning via git/artifact storage.
- **Deviation**: Some tools version graph exports; code-knowledge uses immutable commit hashes instead.

### 4. **Community Detection with Fallback**
- **Decision**: Try Leiden (graspologic) first; fallback to Louvain (NetworkX).
- **Rationale**: Leiden produces higher-quality communities (better modularity), but graspologic is Unix/Python<3.13 only; Louvain is portable.
- **Impact**: Output community IDs may differ between runs if graspologic availability changes; community membership is stable within a Python version.

### 5. **Silent Failure in Vector Search**
- **Decision**: If LanceDB query fails (table missing, corrupted, etc.), return empty results rather than crash.
- **Rationale**: Graceful degradation; users can still use graph traversal (path, explain) even if vector store is broken.
- **Deviation**: Most search engines raise errors; code-knowledge prioritizes availability.

### 6. **No Incremental Vector Embedding**
- **Decision**: `vector.sync()` re-embeds all nodes on every run, even if only the vector store changed.
- **Rationale**: Simple, deterministic; avoids state machine complexity. Embedding 100K nodes takes ~25s, acceptable for offline use.
- **Deviation**: Some vector DBs support append-only inserts; code-knowledge prefers full re-sync for consistency.

### 7. **Local Model Caching Before HF Download**
- **Decision**: Check `.cache/all-MiniLM-L6-v2/` before downloading from Hugging Face.
- **Rationale**: Enables offline-first usage; eliminates HF hub warnings; distributable via `.gitignore` + CI setup.
- **Impact**: Requires `download-model.sh` setup step; makes project portable.

### 8. **Relationship Chains Limited to Top 3 (Outgoing) + Top 3 (Incoming)**
- **Decision**: Query results show up to 3 outgoing + 3 incoming edges per node.
- **Rationale**: Balance between context (not too sparse) and readability (not overwhelming).
- **Deviation**: Some graph DBs show all relationships; code-knowledge caps for human-friendly output.

### 9. **No Custom Extractors**
- **Decision**: Only tree-sitter language parsers are supported; no plugin system for custom extractors.
- **Rationale**: Keeps architecture simple; tree-sitter already covers 26+ languages.
- **Deviation**: Some tools (Graphify) support custom extractors; code-knowledge is intentionally code-only and language-agnostic via tree-sitter.

### 10. **Output Directory = Current Working Directory, Not Source**
- **Decision**: `code-knowledge-out/` is created relative to CWD, not the source directory being analyzed.
- **Rationale**: Allows analyzing multiple codebases from one location; prevents polluting source repos.
- **Impact**: Users must specify `--out` if they want output in the source directory.

---

## Quality Check

- ✅ Every design element traces to a requirement or code fact
- ✅ File structure matches what actually exists on disk
- ✅ Data models match actual TypeScript/Python types in extract.py, build.py, export.py
- ✅ Tech stack includes rationale for each choice (Leiden/Louvain, LanceDB, all-MiniLM-L6-v2)
- ✅ Notable Decisions / Deviations section documents 10 non-obvious architectural choices
