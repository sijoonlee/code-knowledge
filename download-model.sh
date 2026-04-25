#!/usr/bin/env bash
# Download SentenceTransformer model for offline use (project-local cache)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$SCRIPT_DIR/.cache/all-MiniLM-L6-v2"

echo "🔄 Downloading embedding model for offline use..."
echo "📁 Cache directory: $MODEL_DIR"
echo ""

# Create directory if it doesn't exist
mkdir -p "$MODEL_DIR"

# Download the model (use uv run to ensure dependencies are available)
uv run python3 << EOF
import os
from sentence_transformers import SentenceTransformer

model_dir = "$MODEL_DIR"
print(f"Downloading to: {model_dir}")

try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    model.save(model_dir)
    print(f"✓ Model saved successfully")

    # Get directory size
    import subprocess
    result = subprocess.run(["du", "-sh", model_dir], capture_output=True, text=True)
    print(f"✓ Size: {result.stdout.strip()}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
EOF

echo ""
echo "✓ Done! Model cached locally at: .cache/"
echo "  code-knowledge will use the local model (no HF Hub warnings)"
echo ""
echo "To verify:"
echo "  ls -lh $MODEL_DIR"
echo ""
echo "To use in CI/CD: commit .cache/ or add to .gitignore for large repos"
