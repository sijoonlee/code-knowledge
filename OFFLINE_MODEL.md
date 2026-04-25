# Offline Model Setup

## Problem

By default, code-knowledge downloads the SentenceTransformer embedding model (all-MiniLM-L6-v2) from Hugging Face Hub on first use. This causes:

1. **HF Hub warning** in logs:
   ```
   Warning: You are sending unauthenticated requests to the HF Hub. 
   Please set a HF_TOKEN to enable higher rate limits and faster downloads.
   ```

2. **Network dependency**: Requires internet access and Hugging Face availability
3. **Repeated downloads**: Model downloads on first use of `uv run code-knowledge ...`

## Solution

Download the model once to the project-local `.cache/` directory:

```bash
./download-model.sh           # Linux/macOS
powershell -File download-model.ps1  # Windows
```

This:
- ✅ Downloads model to `.cache/all-MiniLM-L6-v2/` (88 MB)
- ✅ Eliminates HF Hub warnings
- ✅ Makes project usable offline
- ✅ Speeds up first vector search query (model cached on disk)

## How It Works

### Code Changes

**vector.py**:
```python
_MODEL_DIR = Path(__file__).parent.parent / ".cache" / "all-MiniLM-L6-v2"

# In sync() and search():
if _MODEL_DIR.exists():
    model = SentenceTransformer(str(_MODEL_DIR))  # Use local
else:
    model = SentenceTransformer("all-MiniLM-L6-v2")  # Download from HF
```

The code checks for a local model first; if not found, falls back to downloading from HF Hub.

### Directory Structure

```
code-knowledge/
├── .cache/
│   └── all-MiniLM-L6-v2/          ← Downloaded model (~88 MB)
│       ├── config.json
│       ├── pytorch_model.bin
│       ├── tokenizer.json
│       └── ...
├── code-knowledge-out/             ← Generated graphs + vectors
├── download-model.sh               ← Run this to download
└── ...
```

## Usage

### First Time Setup

```bash
cd code-knowledge

# Sync dependencies
uv sync --all-extras

# Download embedding model (one-time, ~30 seconds)
./download-model.sh

# Now use offline
uv run code-knowledge update /path/to/code
```

### Subsequent Uses

```bash
# No downloads, uses cached model, no HF warnings
uv run code-knowledge query "what handles messages"
uv run code-knowledge update /path/to/code
```

## CI/CD Integration

### GitHub Actions

```yaml
- uses: astral-sh/setup-uv@v1
  with:
    python-version: "3.11"

- run: uv sync --all-extras

- name: Download embedding model
  run: ./download-model.sh

- name: Build knowledge graph
  run: uv run code-knowledge update /repo/src
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    /root/.cargo/bin/uv sync --all-extras && \
    /root/.cargo/bin/uv run ./download-model.sh

CMD ["uv", "run", "code-knowledge", "update", "/code"]
```

## Storage Considerations

### .cache/ Directory Size

```
all-MiniLM-L6-v2/: ~88 MB
├── pytorch_model.bin: 22 MB    (model weights)
├── tokenizer.json: 213 KB       (tokenizer)
├── config.json: 612 B           (config)
└── ...                          (~65 MB other components)
```

### Options

**Option 1: Commit to git (small repos)**
```bash
git add .cache/
git commit -m "chore: include embedding model"
# Pro: Everything reproducible, no downloads in CI
# Con: Adds 88 MB to repo
```

**Option 2: .gitignore + CI download (recommended)**
```bash
# .gitignore already has: .cache/all-MiniLM-L6-v2/
git add .gitignore
# Pro: Small repo size, fast clones
# Con: CI must download model each time (~30s)
```

**Option 3: Separate artifact storage**
```bash
# Store model in S3/GCS/artifact registry
# Download in CI setup step
# Pro: Very fast CI runs
# Con: Extra infrastructure
```

## Troubleshooting

### Error: "No such file or directory: download-model.sh"
Make sure you're in the `code-knowledge` directory:
```bash
cd code-knowledge
./download-model.sh
```

### Error: "sentence_transformers not found"
The download script uses `uv run` to ensure dependencies. Make sure uv is installed:
```bash
uv --version
uv sync --all-extras
```

### Model not being used locally
Verify the .cache directory:
```bash
ls -lh .cache/all-MiniLM-L6-v2/
```

If empty, re-run:
```bash
./download-model.sh
```

### Still getting HF warnings
Check that the model directory exists and has files:
```bash
ls -la .cache/all-MiniLM-L6-v2/pytorch_model.bin
```

If it exists, the warning should not appear. If it does, there may be a bug in the path detection - open an issue.

## Performance Notes

### First Run After Download

```
uv run code-knowledge query "test"
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]
Loading weights: 100%|██████████| 103/103 [00:00<00:00, 14000.00it/s]
[code-knowledge] Querying: test
...
```

The "Loading weights" is from SentenceTransformer loading the model from disk (~1-2 seconds). This is normal and happens on first query of each command invocation. The model is then cached in Python's process memory for subsequent queries.

### Comparison

| Scenario | Time |
|----------|------|
| First query (no model) | ~30s (download) + 1-2s (load) |
| First query (model cached locally) | ~1-2s (load from disk) |
| Subsequent queries (same process) | <100ms (in-memory) |

---

**Summary**: Run `./download-model.sh` once, then enjoy offline usage with no HF warnings! 🚀
