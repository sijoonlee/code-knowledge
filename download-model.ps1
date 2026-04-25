# Download SentenceTransformer model for offline use (Windows PowerShell, project-local)

Write-Host "🔄 Downloading embedding model for offline use..." -ForegroundColor Green
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelDir = Join-Path $scriptDir ".cache/all-MiniLM-L6-v2"

Write-Host "📁 Cache directory: $modelDir"
Write-Host ""

# Create directory if it doesn't exist
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

# Download the model
Write-Host "Downloading to: $modelDir"

$pythonScript = @"
import os
from sentence_transformers import SentenceTransformer

model_dir = os.path.expanduser("~/.cache/sentence-transformers/all-MiniLM-L6-v2")
print(f"Downloading to: {model_dir}")

try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    model.save(model_dir)
    print(f"✓ Model saved successfully")
    import subprocess
    result = subprocess.run(["powershell", "-Command", f"(Get-Item '{model_dir}' | Measure-Object -Property Length -Recurse).Sum / 1MB"], capture_output=True, text=True)
    print(f"✓ Size: {result.stdout.strip():.1f} MB")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
"@

python3 -c $pythonScript

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Done! Model cached locally." -ForegroundColor Green
    Write-Host "  code-knowledge will now use the local model instead of downloading from HF Hub"
    Write-Host ""
    Write-Host "To verify:" -ForegroundColor Cyan
    Write-Host "  dir $modelDir"
} else {
    Write-Host "✗ Download failed" -ForegroundColor Red
    exit 1
}
