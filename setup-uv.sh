#!/usr/bin/env bash
# Setup code-knowledge with uv

set -e

echo "🚀 Setting up code-knowledge with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Install it with:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv found: $(uv --version)"

# Check Python version
PYTHON_VERSION=$(uv run python --version 2>/dev/null || echo "not found")
echo "✓ Python: $PYTHON_VERSION"

# Sync dependencies
echo ""
echo "📦 Installing dependencies with all extras..."
uv sync --all-extras

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  uv run code-knowledge update /path/to/code"
echo "  uv run code-knowledge query \"what handles auth\""
echo ""
echo "See UV_GUIDE.md for more info."
