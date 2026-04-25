# Using code-knowledge with `uv`

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver, written in Rust.

## Quick Start

### 1. Install uv (if not already installed)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with Homebrew (macOS)
brew install uv
```

### 2. Set up code-knowledge

```bash
cd code-knowledge

# Create virtual environment and install dependencies
uv sync --all-extras

# Or without optional dependencies (uses Louvain instead of Leiden)
uv sync
```

### 3. Run commands

```bash
# Full analysis
uv run code-knowledge update /path/to/code

# Query
uv run code-knowledge query "what handles auth"

# Explore
uv run code-knowledge explain "MyClass"
```

## Why uv?

| Feature | Benefit |
|---------|---------|
| **Fast** | 10-100x faster than pip/poetry for resolving deps |
| **Single binary** | No Python installation needed for installation |
| **Lock file** | `uv.lock` pins exact versions for reproducibility |
| **Virtual envs** | Automatic venv management with `uv sync` |
| **PEP-compliant** | Works with standard `pyproject.toml` |

## Common Commands

```bash
# Install dependencies (creates .venv/)
uv sync

# Add a new dependency
uv add package_name

# Add a dev-only dependency
uv add --dev pytest

# Upgrade all dependencies
uv lock --upgrade

# Run a command in the venv
uv run code-knowledge update .

# Run a script
uv run python script.py

# Enter the venv shell
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# List installed packages
uv pip list

# Remove the venv
rm -rf .venv
```

## Managing Extras

```bash
# Install with all optional dependencies
uv sync --all-extras

# Install only base dependencies
uv sync

# Add new optional dependency group
uv add --optional group-name package_name
```

## Dependency Management

The `uv.lock` file is automatically created and updated by uv. Commit it to version control:

```bash
git add uv.lock
git commit -m "chore: update dependencies via uv"
```

To update dependencies:

```bash
# Update all to latest compatible versions
uv lock --upgrade

# Update a specific package
uv lock --upgrade-package package_name
```

## Performance Comparison

Typical installation time for code-knowledge (26+ tree-sitter languages + lancedb + transformers):

| Tool | Time | Notes |
|------|------|-------|
| **uv** | ~8s | Parallel downloads, fast resolver |
| **pip** | ~45s | Sequential, slower resolver |
| **poetry** | ~60s | Slower lock resolution |

## Troubleshooting

### Issue: `command not found: uv`

**Solution**: Ensure uv is installed and in PATH:
```bash
which uv          # macOS/Linux
where.exe uv      # Windows
```

### Issue: Virtual environment not activated

**Solution**: uv automatically uses `.venv/` created by `uv sync`. If using another tool's venv:
```bash
# Force uv to use current venv
export UV_PROJECT_ENVIRONMENT=.venv
uv sync
```

### Issue: Python version mismatch

**Solution**: uv respects `.python-version` (set to 3.11). Override if needed:
```bash
UV_PYTHON=3.12 uv sync
```

### Issue: Locked graspologic install fails on Windows

**Cause**: graspologic requires compilation; not available for Windows in Python 3.13+

**Solution**: Use without Leiden:
```bash
uv sync  # Skips graspologic, uses Louvain instead
```

## Tips

- **Use `uv run`** instead of activating venv for one-off commands
- **Commit `uv.lock`** to git for reproducible environments across CI/CD
- **Use `uv.lock --upgrade`** regularly to get security patches
- **Set `UV_CACHE_DIR`** to share downloads across projects (faster for repeated deps)

---

For more info, see [uv documentation](https://docs.astral.sh/uv/).
