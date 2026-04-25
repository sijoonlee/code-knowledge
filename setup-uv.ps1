# Setup code-knowledge with uv (Windows PowerShell)

Write-Host "🚀 Setting up code-knowledge with uv..." -ForegroundColor Green

# Check if uv is installed
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host "❌ uv is not installed. Install it with:" -ForegroundColor Red
    Write-Host "   powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ uv found: $(uv --version)" -ForegroundColor Green

# Check Python version
try {
    $pythonVersion = uv run python --version 2>$null
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠ Could not detect Python version" -ForegroundColor Yellow
}

# Sync dependencies
Write-Host ""
Write-Host "📦 Installing dependencies with all extras..." -ForegroundColor Green
uv sync --all-extras

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Setup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  uv run code-knowledge update C:\path\to\code"
    Write-Host "  uv run code-knowledge query `"what handles auth`""
    Write-Host ""
    Write-Host "See UV_GUIDE.md for more info."
} else {
    Write-Host "❌ Setup failed" -ForegroundColor Red
    exit 1
}
