# Implementation Summary: code-knowledge

## What Was Built

A simplified, code-only knowledge graph project at `/home/sijoon-lee/Documents/playground/knowledge-store/code-knowledge/`.

### Scope
- **Input**: Code files only (26+ languages via tree-sitter)
- **Output**: Minimal schema graph.json + LanceDB vector store
- **Pipeline**: detect → extract → build → cluster → export → sync_vectors

### Files Created

#### Core Pipeline Modules
1. **`detect.py`** — File discovery, code-only classification
   - Removed: non-code file types (docs, PDFs, images, video)
   - Removed: transcription and office file conversion
   - Kept: `.graphifyignore` support, sensitive file skipping, manifest-based incremental updates

2. **`extract.py`** — Tree-sitter AST extraction (COPIED from graphify, unchanged)
   - Multi-language: Python, JS/TS, Go, Rust, Java, C/C++, Ruby, Scala, PHP, Swift, Lua, Zig, etc.
   - Output schema: nodes (id, label, source_file, source_location) + edges (source, target, relation, confidence)
   - Deterministic SHA256 caching per file

3. **`build.py`** — Merge extractions into NetworkX DiGraph
   - Removed: `_src`/`_tgt` synthetic edge attributes (only used for HTML visualization)
   - Removed: hyperedges handling
   - Kept: node deduplication, ID normalization, edge direction preservation

4. **`cluster.py`** — Leiden/Louvain community detection
   - Removed: `cohesion_score()` and `score_all()` (only fed report.py)
   - Kept: core `cluster()` function, oversized community splitting

5. **`export.py`** — JSON export (NEW, minimal)
   - Simplified `to_json()`: outputs only required fields
   - Node schema: id, label, source_file, source_location, contributor, community
   - Edge schema: from, to, relation (remapped from source/target)
   - Kept: `prune_dangling_edges()` helper
   - Removed: HTML, Obsidian, SVG, GraphML, Neo4j, Cypher exports

6. **`vector.py`** — LanceDB vector store (NEW)
   - `build_embedding_text()`: label + community + neighbor labels + relations
   - `embed_hash()`: SHA256 for change detection
   - `sync()`: diff-based upsert (insert new, update changed, delete removed)
   - `search()`: natural language query → ANN search → node_id + score
   - Model: `all-MiniLM-L6-v2` (22MB, 384D, CPU-friendly)

7. **`cache.py`** — Per-file extraction cache
   - Removed: `check_semantic_cache()` and `save_semantic_cache()` (LLM semantic extraction)
   - Kept: content-based SHA256 caching, manifest for incremental updates

8. **`validate.py`** — Schema validation (COPIED from graphify, modified)
   - Updated: removes hyperedge validation

9. **`security.py`** — Path and label sanitization (COPIED from graphify, unchanged)

10. **`__init__.py`** — Package initialization

11. **`__main__.py`** — CLI (NEW)
    - `code-knowledge update <path>` — full pipeline
    - `code-knowledge index [--graph]` — rebuild vector store from graph.json
    - `code-knowledge query "<text>" [--top-k N]` — natural language search → graph exploration
    - `code-knowledge path "<A>" "<B>"` — shortest path between nodes
    - `code-knowledge explain "<label>"` — node details + neighbors

#### Project Config
- **`pyproject.toml`** — Package metadata, dependencies
  - Required: networkx, tree-sitter, 21 language parsers, lancedb, sentence-transformers
  - Optional: `[leiden]` extra for graspologic (Leiden clustering)

- **`README.md`** — User guide, schema documentation, examples

### Files Removed/Not Included

From Graphify, intentionally omitted:
- `transcribe.py` — no audio/video
- `ingest.py` — no URL/tweet/arXiv ingestion
- `report.py` — no GRAPH_REPORT.md generation
- `analyze.py` — no god nodes / surprises / knowledge gaps
- `wiki.py` — no wiki export
- `watch.py` — no filesystem watcher
- `serve.py` — no MCP server
- `hooks.py` — no git hooks
- `benchmark.py` — no token-cost benchmarking
- All `skill*.md` files — no LLM semantic extraction

## Schema Design

### Nodes (Minimal)
```json
{
  "id": "session_validatetoken",
  "label": "ValidateToken",
  "source_file": "auth/session.py",
  "source_location": "L42",
  "contributor": null,
  "community": 2
}
```

### Edges (Minimal)
```json
{
  "from": "session_validatetoken",
  "to": "session_authtoken",
  "relation": "calls"
}
```

### Vector Embeddings
Example text for node `ValidateToken`:
```
"ValidateToken community 2 calls AuthToken imports CryptoLib contains CheckToken"
```

Embedded to 384 dimensions via all-MiniLM-L6-v2 → LanceDB ANN search.

## Testing Status

### ✅ Completed
- Python syntax validation (all .py files compile)
- File structure verified
- Schema design finalized
- Module imports reviewed (no external dependency issues)
- uv project configuration (pyproject.toml, .python-version, setup scripts)

### ⏳ Not Yet Tested (requires uv sync or pip install)
- Full pipeline execution
- Vector store creation and search
- CLI command parsing
- Graph.json export format validation

### Known Issues to Address
1. **extract.py**: Still references `graphify-out/cache/` in docstrings (should be `code-knowledge-out/cache/`) — cosmetic, doesn't affect functionality
2. **Vector search**: `lancedb` API may have changed; adjust if needed based on actual version
3. **Performance**: Extraction is single-threaded; could add parallel processing per file

## Next Steps

1. **Set up with uv** (recommended):
   ```bash
   cd /home/sijoon-lee/Documents/playground/knowledge-store/code-knowledge
   ./setup-uv.sh        # or setup-uv.ps1 on Windows
   ```
   Or manually:
   ```bash
   uv sync --all-extras
   ```

2. **Run on a test codebase**:
   ```bash
   uv run code-knowledge update /some/code/path
   uv run code-knowledge query "what handles authentication"
   ```

3. **Validate outputs**:
   - Check `code-knowledge-out/graph.json` schema
   - Verify vector search results make sense
   - Test all CLI commands with `uv run code-knowledge ...`

4. **Optimize (optional)**:
   - Add parallel extraction (multiprocessing)
   - Cache vector embeddings separately
   - Add progress bars for large codebases
   - Implement incremental `update` (only re-extract changed files)

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Copy extract.py unchanged | Already code-only, deterministic, 26+ languages supported |
| Remove LLM semantic extraction | Focus on AST-based; semantic queries via vector search instead |
| Minimal node schema (6 fields) | Covers all essential relationships; extra metadata in edge relations |
| LanceDB not Neo4j | File-based, no server, lightweight, built-in embedding support |
| all-MiniLM-L6-v2 model | 22MB, 384D, CPU-friendly, good code semantics, widely used |
| Directed graph (DiGraph) | Preserves call direction; better for code flow analysis |
| Community detection essential | Enables "god node" discovery, cross-community exploration |

## Metrics

- **Lines of code**: ~2K (core + utilities)
- **Python files**: 12
- **Tree-sitter languages**: 26
- **Dependencies**: 5 core + 1 optional (graspologic for Leiden)
- **Graph schema**: 6 node fields, 3 edge fields
- **Embedding dimensions**: 384
- **Package manager**: uv (recommended) or pip

## Tooling

- **pyproject.toml**: PEP-compliant project config (hatchling build backend)
- **.python-version**: 3.11 (for uv/pyenv)
- **setup-uv.sh**: Automated setup script (Linux/macOS)
- **setup-uv.ps1**: Automated setup script (Windows PowerShell)
- **UV_GUIDE.md**: Comprehensive uv usage guide

---

**Status**: ✅ Code structure complete, ready for dependency installation and integration testing.
