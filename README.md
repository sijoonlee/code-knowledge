# code-knowledge

Code-only knowledge graph with vector search. A simplified version of Graphify focused on analyzing codebases using tree-sitter AST extraction and LanceDB vector embeddings.

## Disclaimer
- This is [graphify clone](https://github.com/safishamsi/graphify)
- Data structure is much more simplified than Graphify
- Only ingests code
- No other formats such as video is supported
- You can use Semantic search

## Features

- **Multi-language code analysis**: Supports 26+ languages via tree-sitter (Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, Ruby, Scala, PHP, etc.)
- **Deterministic AST extraction**: No LLM calls, fast and reproducible
- **Community detection**: Groups related code via Leiden/Louvain clustering
- **Vector search**: Find code by natural language queries, powered by sentence-transformers + LanceDB
- **Graph traversal**: Explore relationships: calls, imports, data flow

## Installation

### With `uv` (recommended)

```bash
# Install dependencies in a virtual environment
uv sync --all-extras

# Or without Leiden (fallback to Louvain)
uv sync

# (Optional) Download embedding model for offline use
./download-model.sh           # Linux/macOS
powershell -File download-model.ps1  # Windows
```

### With `pip`

```bash
cd code-knowledge
pip install -e ".[leiden]"
```

### Dependencies

This installs:
- `networkx` ≥3.0 — graph algorithms
- `tree-sitter` ≥0.23.0 + 21 language parsers
- `lancedb` — vector database
- `sentence-transformers` — embeddings (all-MiniLM-L6-v2)
- `graspologic` (optional `leiden` extra) — Leiden clustering (Linux/macOS, Python <3.13; Windows falls back to Louvain)

## Usage

### Build a knowledge graph

Analyze a codebase and build the graph + vector store:

```bash
uv run code-knowledge update /path/to/code
```

Outputs:
- `code-knowledge-out/graph.json` — 6-field minimal schema for nodes and edges
- `code-knowledge-out/vectors/` — LanceDB vector store

### Query by natural language

```bash
uv run code-knowledge query "what handles authentication"
```

Returns top-10 matching nodes with metadata and neighbors.

### Shortest path

```bash
uv run code-knowledge path "Session" "AuthToken"
```

### Node details

```bash
uv run code-knowledge explain "ValidateToken"
```

Shows metadata, outgoing calls, and incoming references.

### Rebuild vector store (no re-extract)

```bash
uv run code-knowledge index
```

### Or, install as a tool

```bash
# Add to PATH for direct execution
uv tool install --editable .

code-knowledge update /path/to/code
code-knowledge query "what handles authentication"
```

## Offline Usage

By default, code-knowledge downloads the embedding model (22MB) from Hugging Face Hub on first use. To avoid the HF warning and use offline:

```bash
# Download model once (requires internet)
./download-model.sh           # Linux/macOS
powershell -File download-model.ps1  # Windows

# Then all subsequent uses work offline
uv run code-knowledge update /path/to/code
uv run code-knowledge query "..."
```

The model is cached in the project at `.cache/all-MiniLM-L6-v2/` and reused for all future runs. This makes the project portable and CI/CD-friendly:

- **For CI/CD**: Commit `.cache/` to git or download it as part of setup
- **For development**: Run `download-model.sh` once, then work offline
- **Size**: ~350 MB (all-MiniLM-L6-v2 + tokenizers)

---

## Schema

### Nodes

| Field | Type | Example |
|-------|------|---------|
| `id` | str | `"session_validatetoken"` |
| `label` | str | `"ValidateToken"` |
| `source_file` | str | `"auth/session.py"` |
| `source_location` | str | `"L42"` |
| `contributor` | str \| null | `null` |
| `community` | int | `2` |

### Edges

| Field | Type | Example |
|-------|------|---------|
| `from` | str | `"session_validatetoken"` |
| `to` | str | `"session_authtoken"` |
| `relation` | str | `"calls"` |

Built-in relation types: `calls`, `imports`, `imports_from`, `contains`, `inherits`, `extends`, `implements`, `references`, `cites`, `conceptually_related_to`, `shares_data_with`, `semantically_similar_to`, `rationale_for`

### Vector embeddings

Each node is embedded as:
```
"{label} community {community_id} {relation} {neighbor_label} {relation} {neighbor_label} ..."
```

Example:
```
"Session community 0 imports authutil imports crypto contains validatetoken"
```

The embedding captures semantic context: the node's purpose (label), its community cohort, and its direct relationships.

## Architecture

```
detect(root)                  → find code files
    ↓
extract(files)               → AST extraction via tree-sitter
    ↓
build_graph(extractions)     → merge into NetworkX DiGraph
    ↓
cluster(G)                   → community detection (Leiden/Louvain)
    ↓
export(G, communities)       → graph.json
    ↓
sync_vectors(G)              → LanceDB vector store
```

Each stage is independent; you can skip vector syncing if you only need the graph.

## Development

### Run on the project itself

```bash
uv sync --all-extras
uv run code-knowledge update .
uv run code-knowledge query "what extracts code"
uv run code-knowledge explain "extract"
```

### Structure

- `detect.py` — code file discovery and filtering
- `extract.py` — tree-sitter AST walkers (21 languages)
- `build.py` — merge extractions into NetworkX graph
- `cluster.py` — Leiden/Louvain community detection
- `export.py` — export to graph.json
- `vector.py` — LanceDB sync and semantic search
- `cache.py` — per-file extraction cache (by SHA256)
- `security.py` — path and label sanitization
- `validate.py` — schema validation
- `__main__.py` — CLI commands

### Adding a language

1. Install `tree-sitter-<lang>` package
2. Add `extract_<lang>(path)` function in `extract.py`
3. Register in the `_DISPATCH` dict
4. Add to `CODE_EXTENSIONS` in `detect.py`

## Performance

Typical results on a 50K-file Python monorepo:

| Stage | Time | Notes |
|-------|------|-------|
| detect | 2s | filesystem walk |
| extract | 60s | 50 files/sec single-threaded |
| build | 5s | merge + dedup |
| cluster | 8s | 500K edges |
| export | 3s | JSON serialization |
| vector | 25s | embedding + LanceDB upsert |

Total: ~2 minutes for 50K files / 100K nodes.

## Limitations

- **Tree-sitter coverage**: Functional code idioms (closures, pipes, higher-order functions) are partially supported; anonymous lambdas are skipped. Semantic extraction is code-based only (no LLM).
- **Large graphs**: Vector search scales to ~1M nodes; UI graph visualization is limited to 5K nodes.
- **Precision**: Extraction is AST-based (deterministic but not perfect). Cross-file call resolution is heuristic.

## License

MIT
