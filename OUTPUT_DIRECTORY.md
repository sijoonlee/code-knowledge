# Output Directory Behavior

## Default Behavior

By default, `code-knowledge update` creates output in:
```
./code-knowledge-out/
```

Where `./` is the **current working directory** when you run the command, NOT the source directory being analyzed.

## Example

```bash
# Scenario: Analyzing kafkajs from the code-knowledge project
cd /home/sijoon-lee/Documents/playground/knowledge-store/code-knowledge

# Output goes HERE:
uv run code-knowledge update /home/sijoon-lee/Documents/playground/knowledge-store/kafkajs
# → Creates: /home/sijoon-lee/.../code-knowledge/code-knowledge-out/
# → NOT: /home/sijoon-lee/.../kafkajs/code-knowledge-out/
```

## Why Two Locations?

If you found `code-knowledge-out/` in two places, you probably:

1. **First run** from code-knowledge directory:
   ```bash
   cd ~/code-knowledge
   uv run code-knowledge update ~/kafkajs
   # → Creates: ~/code-knowledge/code-knowledge-out/
   ```

2. **Second run** from kafkajs directory:
   ```bash
   cd ~/kafkajs
   uv run code-knowledge update .
   # → Creates: ~/kafkajs/code-knowledge-out/
   ```

## Controlling Output Location

### Method 1: Use `--out` flag (recommended)
```bash
# Explicitly specify output directory
uv run code-knowledge update /path/to/code --out ~/graphs/myproject-graph
```

### Method 2: Change working directory
```bash
# Output goes to ./code-knowledge-out/ relative to here
cd ~/graphs
uv run code-knowledge update /path/to/code
```

### Method 3: Use absolute paths in scripts
```bash
#!/bin/bash
GRAPH_DIR="$HOME/graphs/$(basename $1)"
cd "$(dirname "$GRAPH_DIR")"
uv run code-knowledge update "$1" --out "$GRAPH_DIR"
```

## Best Practices

### For Single Projects
```bash
# Analyze your codebase, output to ./code-knowledge-out/
cd ~/myproject
uv run code-knowledge update .
```

### For Multiple Projects
```bash
# Keep graphs organized
for project in projects/*; do
  uv run code-knowledge update "$project" \
    --out "graphs/$(basename $project)"
done
```

### For CI/CD
```yaml
- name: Build knowledge graph
  run: |
    uv run code-knowledge update . \
      --out "${{ github.workspace }}/build/graph"
```

## Output Structure

Regardless of location, the output contains:

```
code-knowledge-out/
├── graph.json           # Graph with 6-field node schema
├── vectors/             # LanceDB vector store
│   └── nodes.lance
├── cache/               # Extraction cache (SHA256-based)
│   ├── xxxxxxx.json
│   └── ...
└── manifest.json        # File mtime manifest for incremental updates
```

---

**TL;DR**: Output goes to `./code-knowledge-out/` in your **current directory**. Use `--out` flag to change it explicitly.
