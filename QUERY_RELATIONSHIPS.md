# Query with Relationship Chains

## Overview

The `query` command now combines **vector semantic search** + **graph relationship chains**:

```
User query: "message broker connection"
       ↓
Vector search finds relevant nodes (semantic matching)
       ↓
Display immediate relationships (calls, uses, called_by, imports)
       ↓
Rich context for understanding the codebase
```

## How It Works

### 1. Vector Search (Entry Points)
Finds semantically similar nodes based on natural language:
```bash
uv run code-knowledge query "how to authenticate"
```

Results are ranked by relevance score (lower = better match).

### 2. Relationship Chains
For each result, shows:
- **➡️ This node calls/imports/uses**: Outgoing edges (dependencies)
- **⬅️ Called/used by**: Incoming edges (who depends on this)

## Example

```
Query: "message broker connection"

1. broker() (relevance: 0.968)
   📄 File: src/protocol/requests/metadata/v1/response.js
   📍 Location: L24
   👥 Community: 6
   ⬅️ Called/used by:
      response.js → contains

2. .authenticate() (relevance: 1.171)
   📄 File: src/broker/saslAuthenticator/scram.js
   📍 Location: L130
   👥 Community: 8
   ➡️ This node:
      calls → .sendClientFirstMessage()
      calls → .sendClientFinalMessage()
      calls → .serverKey()
   ⬅️ Called/used by:
      SCRAM → method
```

## Relationship Types

The chains show different types of relationships:

| Type | Meaning | Example |
|------|---------|---------|
| `calls` | Direct function/method invocation | `authenticate() calls validateToken()` |
| `imports` | Module/library import | `handler imports logger` |
| `imports_from` | Specific import from module | `handler imports_from utils validateInput` |
| `contains` | File contains function/class | `index.js contains consumer()` |
| `uses` | Generic usage/dependency | `retry uses exponentialBackoff()` |
| `method` | Method on object | `SCRAM method authenticate()` |

## Understanding the Flow

### Outgoing Relationships (➡️)
Shows what this node **depends on**:
```
authenticate() calls:
  → sendClientFirstMessage()
  → sendClientFinalMessage()
```
Useful for: "What does this function do internally?"

### Incoming Relationships (⬅️)
Shows what **depends on this node**:
```
authenticate() called by:
  ← SCRAM → method
```
Useful for: "Where is this function used?"

## Use Cases

### 1. Understanding a Single Function
```bash
$ uv run code-knowledge query "authenticate"

→ See what authenticate() calls (implementation details)
→ See what calls authenticate() (usage context)
```

### 2. Finding Integration Points
```bash
$ uv run code-knowledge query "connect to broker"

→ Find broker connection classes
→ See what they call (dependencies)
→ See what uses them (consumers)
```

### 3. Tracing Data Flow
```bash
$ uv run code-knowledge query "message serialization"

→ Find serialization functions
→ See what they're called from
→ Follow the chain upward to find message producers
```

## Tips

### Get More Context
Multiple queries reveal the full picture:

```bash
# Start with semantic search
uv run code-knowledge query "producer"

# Then deep-dive on one result
uv run code-knowledge explain "Producer"

# Follow a relationship chain
uv run code-knowledge path "Producer" "Broker"
```

### Filter by Community
Results grouped by community help understand architecture:
```
Community 0: Core API
Community 6: Protocol handling
Community 8: Authentication
```

### Score Interpretation
- **Lower score = better match** (vector distance)
- **0.5**: Highly relevant
- **1.0+**: Still relevant but less precise
- **2.0+**: Tangentially related

## Implementation Details

The relationship chains are extracted from the graph in real-time:

- **Outgoing edges**: `G.out_edges(node)` - what this node calls/imports
- **Incoming edges**: `G.in_edges(node)` - what calls/imports this node
- **Limit**: Shows top 3 for each direction (configurable)

## Examples

### Example 1: Error Handling Flow
```bash
$ uv run code-knowledge query "error handling"

isErrorRetriable() (relevance: 0.92)
  ➡️ This node:
      calls → isErrorUnrecoverable()
  ⬅️ Called/used by:
      retry → calls
      exponentialBackoff → uses
```

### Example 2: Configuration
```bash
$ uv run code-knowledge query "configuration settings"

Config (relevance: 0.88)
  ➡️ This node:
      imports → parseEnv()
      calls → validateSchema()
  ⬅️ Called/used by:
      Client → imports
      Admin → imports
```

---

**Tip**: Use `query` for semantic exploration and `explain` for detailed deep-dives on specific nodes.
