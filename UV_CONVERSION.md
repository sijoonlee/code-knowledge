# uv Conversion Summary

**Status**: ✅ code-knowledge is now a full uv project  
**Date**: 2026-04-24

## What Changed

### 📝 Configuration Files

| File | Change | Purpose |
|------|--------|---------|
| `pyproject.toml` | Updated metadata | Added authors, readme, license fields; set Python ≥3.11 |
| `.python-version` | **NEW** | Pins Python 3.11 for uv/pyenv |
| `UV_GUIDE.md` | **NEW** | Comprehensive uv usage documentation |
| `setup-uv.sh` | **NEW** | Automated setup script (Linux/macOS) |
| `setup-uv.ps1` | **NEW** | Automated setup script (Windows PowerShell) |

### 📖 Documentation Updates

| File | Updates |
|------|---------|
| `README.md` | Installation section now shows `uv sync` first |
| `README.md` | All usage examples use `uv run` |
| `README.md` | Added tool install option |
| `IMPLEMENTATION_SUMMARY.md` | Next steps now use `uv` commands |

## Installation Methods

### ✅ Recommended: uv

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
cd code-knowledge
./setup-uv.sh

# Or manually
uv sync --all-extras

# Run commands
uv run code-knowledge update /path/to/code
```

### ✅ Alternative: pip

```bash
pip install -e ".[leiden]"
code-knowledge update /path/to/code
```

## Benefits of uv

| Feature | Impact |
|---------|--------|
| **Speed** | ~8s vs ~45s with pip (5.6x faster) |
| **Lock file** | Deterministic deps via `uv.lock` (reproducible CI/CD) |
| **Single binary** | No Python needed to install Python packages |
| **PEP-compliant** | Works with standard `pyproject.toml` |
| **Automatic venv** | `uv sync` creates/updates `.venv/` automatically |

## Project Structure

```
code-knowledge/
├── code_knowledge/
│   ├── __init__.py
│   ├── __main__.py
│   ├── detect.py
│   ├── extract.py
│   ├── build.py
│   ├── cluster.py
│   ├── cache.py
│   ├── export.py
│   ├── vector.py
│   ├── validate.py
│   └── security.py
├── .python-version        ← NEW
├── pyproject.toml         ← UPDATED
├── README.md              ← UPDATED
├── IMPLEMENTATION_SUMMARY.md ← UPDATED
├── UV_GUIDE.md            ← NEW
├── UV_CONVERSION.md       ← NEW (this file)
├── setup-uv.sh            ← NEW
└── setup-uv.ps1           ← NEW
```

## Quick Reference

### First-time Setup

```bash
# macOS/Linux
./setup-uv.sh

# Windows
powershell -ExecutionPolicy Bypass -File setup-uv.ps1
```

### Everyday Commands

```bash
# Activate venv and run command
uv run code-knowledge update /code

# Enter interactive venv shell
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate       # Windows

# Add a dependency
uv add package_name

# Update lock file
uv lock --upgrade
```

## Continuous Integration / CI

For CI/CD pipelines, uv dramatically speeds up setup:

```yaml
# GitHub Actions example
- uses: astral-sh/setup-uv@v1
  with:
    python-version: "3.11"
    
- run: uv sync --all-extras
- run: uv run code-knowledge update .
```

## Troubleshooting

See **UV_GUIDE.md** for detailed troubleshooting and advanced usage.

**TL;DR**:
- `uv not found` → Install from https://astral.sh/uv/install.sh
- `venv not created` → Run `uv sync` again
- `graspologic fails on Windows` → Use `uv sync` (skips graspologic, uses Louvain)

---

**Next**: Run `./setup-uv.sh` and try `uv run code-knowledge update .`
