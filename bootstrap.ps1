$RequiredMajor = 3
$RequiredMinor = 10

Write-Host "🔍 Checking Python version..."

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "❌ Python not found. Install Python 3.10 first."
    exit 1
}

$versionInfo = python -c "import sys; print(sys.version_info.major, sys.version_info.minor)"
$parts = $versionInfo.Split(" ")

$major = [int]$parts[0]
$minor = [int]$parts[1]

if ($major -ne $RequiredMajor -or $minor -ne $RequiredMinor) {
    Write-Host "❌ Python 3.10 required. Found $major.$minor"
    exit 1
}

Write-Host "✅ Python 3.10 detected"

Write-Host "📦 Creating virtual environment..."
python -m venv .venv

Write-Host "⚙️ Activating virtual environment..."
. .\.venv\Scripts\Activate.ps1

Write-Host "⬇️ Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.lock
pip install -e .

Write-Host "🎉 Podvoice is ready!"
Write-Host "👉 Run: .venv\Scripts\Activate.ps1"
Write-Host "👉 Then: podvoice --help"