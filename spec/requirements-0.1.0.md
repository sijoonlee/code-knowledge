# code-knowledge Requirements v0.1.0

## Service Overview

**Purpose**: Enable developers to analyze arbitrary multi-language codebases by building knowledge graphs with vector search, without requiring LLM calls. Users can discover code structure, find related functionality, and understand relationships through both graph traversal and natural language queries.

**Scope**: Code analysis and discovery only. Does not handle non-code content, does not provide code generation or modification, does not perform semantic analysis beyond AST extraction.

---

## User Stories

### Build Graph Workflow

#### US-1: Full pipeline from codebase to queryable graph
**As a** developer or automation system,  
**I want to** run `code-knowledge update /path/to/code` to analyze a codebase,  
**So that** I can build a searchable knowledge graph of its structure.

**Acceptance Criteria**:
- Command accepts a root directory path (relative or absolute)
- Scans directory recursively and identifies all code files based on extension (26+ languages supported: `.py`, `.ts`, `.js`, `.jsx`, `.tsx`, `.go`, `.rs`, `.java`, `.cpp`, `.c`, `.h`, `.rb`, `.swift`, `.kt`, `.cs`, `.scala`, `.php`, `.lua`, `.zig`, `.ps1`, `.ex`, `.m`, `.jl`, `.vue`, `.svelte`, `.dart`, `.v`)
- Skips non-code artifacts: `node_modules/`, `.venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `target/`, lock files (`package-lock.json`, `Cargo.lock`, etc.), and `code-knowledge-out/` directories
- Skips files with sensitive patterns (`.env`, `.pem`, `.key`, credentials, passwords, SSH keys, AWS credentials)
- Per-file extraction is cached by SHA256 hash; unchanged files reuse cached extraction on re-run
- Merges all file extractions into a single directed graph
- Detects code communities using Leiden (Unix/Python<3.13) or Louvain clustering
- Exports graph to `code-knowledge-out/graph.json` by default, or `--out` flag path
- Syncs nodes to LanceDB vector store at `code-knowledge-out/vectors/`
- Pipeline stages: detect → extract → build → cluster → export → sync_vectors
- Output location: `./code-knowledge-out/` relative to current working directory, not source directory
- Command prints progress: file count, graph dimensions (node/edge counts), community count, and completion
- [inferred] On error in any stage (e.g., permission denied, parse failure), stops with exit code 1 and error message to stderr

**Non-Functional Requirements**:
- Extraction throughput: ~50 files/sec on single-threaded AST parsing
- Graph export: JSON format readable by NetworkX (node-link format)
- Cache: Stores extracted nodes/edges as JSON in `code-knowledge-out/cache/{hash}.json`

#### US-2: Rebuild vector store without re-extraction
**As a** developer who has modified the embedding model or clustering,  
**I want to** run `code-knowledge index [--graph path/to/graph.json]` to re-sync vectors,  
**So that** I can regenerate the vector store without waiting for re-extraction.

**Acceptance Criteria**:
- Loads existing `graph.json` (default: `code-knowledge-out/graph.json`)
- Creates/updates LanceDB vector store in `code-knowledge-out/vectors/`
- Does not re-run detect, extract, build, or cluster phases
- Completes in ~25s for 100K nodes (embedding + LanceDB upsert)
- Prints progress: node count and sync statistics

---

### Query Workflow

#### US-3: Semantic search by natural language query
**As a** developer exploring unfamiliar code,  
**I want to** run `uv run code-knowledge query "what handles authentication"` to find relevant nodes,  
**So that** I can discover code that matches my semantic intent.

**Acceptance Criteria**:
- Accepts query string as positional argument
- Searches vector store using sentence-transformers embedding (all-MiniLM-L6-v2, 384-dim)
- Returns up to `--top-k` results (default: 10) ranked by relevance score
- Relevance score is vector distance: lower = more relevant
- For each result, displays:
  - Rank number, node label, and relevance score
  - Source file path
  - Source location (line number)
  - Assigned community ID
  - Outgoing relationships: up to 3 edges (what this node calls/imports)
  - Incoming relationships: up to 3 edges (what calls/uses this node)
- Relationship display shows: `{relation_type} → {target_label}` for outgoing, `{source_label} → {relation_type}` for incoming
- If no results found, prints "[code-knowledge] No results found"
- Requires `code-knowledge-out/vectors/` and `code-knowledge-out/graph.json` to exist; exits with error if missing

**Non-Functional Requirements**:
- Query embedding and search: <1s for 100K nodes (after model load)
- Model download fallback: If local model not found at `.cache/all-MiniLM-L6-v2/`, downloads from Hugging Face Hub (shows HF warning; ~30s first time)
- Output includes emoji annotations (📄, 📍, 👥, ➡️, ⬅️) for visual clarity

#### US-4: Find shortest path between two code entities
**As a** developer understanding call chains,  
**I want to** run `code-knowledge path "AuthToken" "Session"` to find the call chain between two nodes,  
**So that** I can trace data flow and understand dependencies.

**Acceptance Criteria**:
- Accepts two positional arguments: node labels (A, B)
- Finds both nodes in the graph by exact label match
- Computes shortest path using NetworkX algorithm (unweighted, breadth-first)
- Displays path as list of node labels in traversal order (A → ... → B)
- Prints path length (number of nodes)
- If either node not found, exits with error: "[code-knowledge] ERROR: could not find nodes for '{A}' and '{B}'"
- If no path exists, prints "[code-knowledge] No path found between '{A}' and '{B}'"

#### US-5: Inspect node and its immediate relationships
**As a** developer deep-diving into a specific function or class,  
**I want to** run `code-knowledge explain "ValidateToken"` to see all its details and neighbors,  
**So that** I can understand what it calls and what calls it.

**Acceptance Criteria**:
- Accepts node label as positional argument
- Finds node by exact label match
- Displays node metadata:
  - ID (internal graph identifier)
  - Label
  - Source file and location
  - Assigned community ID
  - Contributor (if present in graph, else "unknown")
- Lists outgoing edges: up to 10 of "Calls/references" with format `{relation_type} → {target_label}`
- Lists incoming edges: up to 10 of "Called by" with format `{source_label} → {relation_type}`
- If node not found, exits with error: "[code-knowledge] ERROR: node '{label}' not found"

---

## Non-Functional Requirements (Cross-Cutting)

### Configuration & Runtime
- Python 3.11+ required
- Dependencies: NetworkX ≥3.0, tree-sitter ≥0.23.0, LanceDB, sentence-transformers, optional graspologic for Leiden
- Output directory customizable via `--out` flag; default is `./code-knowledge-out/` relative to CWD
- Graph path customizable via `--graph` flag; default is `code-knowledge-out/graph.json`
- Query result limit customizable via `--top-k` flag; default 10
- All CLI commands have `--help` option

### Data Integrity
- Graph export refuses to silently shrink existing graph.json (anti-corruption check): warns and skips if new graph has fewer nodes unless `force=True`
- All file paths are resolved to absolute paths before processing
- Edge deletion in vector store uses SQL-like syntax: `id = '{node_id}'`
- [inferred] Sensitive files are skipped during detection, not logged by default

### Error Handling
- File I/O errors: caught and logged to stderr with exit code 1
- Graph load errors: exits with error message if graph.json malformed
- Vector store errors: silent failure in search (returns empty results) rather than crashing
- Path not found: exits with descriptive error

### Embedding & Vectors
- Each node embedded as: `"{label} community {community_id} {relation} {neighbor_label} ..."` 
- Embedding includes node label, community ID, and up to all outgoing edges
- Vector store uses LanceDB with auto-generated vector IDs matching node IDs
- Sync operation inserts new nodes, deletes removed nodes, updates changed nodes (detected by SHA256 hash of embedding text)
- Supports both fetching all vectors for sync and ANN search for queries

---

## Data Schema

### Nodes (output to graph.json)
| Field | Type | Required | Example |
|-------|------|----------|---------|
| id | string | Yes | `"session_validatetoken"` |
| label | string | Yes | `"ValidateToken"` |
| source_file | string | Yes | `"auth/session.py"` |
| source_location | string | Yes | `"L42"` |
| contributor | string \| null | No | `null` or `"alice"` |
| community | int | Yes | `2` |

### Edges (output to graph.json)
| Field | Type | Required | Example |
|-------|------|----------|---------|
| source | string | Yes | `"session_validatetoken"` |
| target | string | Yes | `"session_authtoken"` |
| relation | string | Yes | `"calls"` |

**Supported relations**: `calls`, `imports`, `imports_from`, `contains`, `inherits`, `extends`, `implements`, `references`, `cites`, `conceptually_related_to`, `shares_data_with`, `semantically_similar_to`, `rationale_for`

### Vector Store (LanceDB)
| Field | Type | Example |
|-------|------|---------|
| id | string | `"session_validatetoken"` |
| text | string | `"ValidateToken community 2 calls sendRequest imports crypto"` |
| embedding | vector[384] | (auto-generated by SentenceTransformer) |
| embed_hash | string | SHA256 hex digest |

---

## Out of Scope

- **Non-code content**: No support for Markdown, PDFs, videos, images, or office documents
- **Code generation**: Does not generate, refactor, or modify code
- **Semantic analysis**: Does not use LLMs; only performs AST-based extraction
- **Real-time analysis**: One-shot batch processing; no live monitoring
- **Custom extractors**: Users cannot register custom language parsers (tree-sitter only)
- **Graph visualization**: No built-in UI; JSON export for external tools
- **Incremental updates**: Full re-scan required; does not support differential indexing
- **Cross-repository linking**: Analyzes single codebase at a time

---

## Discrepancies

**None identified.**

---

## Quality Check

- ✅ All capabilities have a user story (5 stories covering all CLI commands)
- ✅ Acceptance criteria are verifiable (exit codes, output formats, dimensions, latency)
- ✅ NFRs have measurable thresholds (50 files/sec, ~25s for 100K nodes, <1s queries, ~30s model download)
- ✅ Out-of-scope items explicitly listed
- ✅ No discrepancies found in code vs. documented behavior
