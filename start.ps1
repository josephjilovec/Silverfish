$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'Starting SilverTrap. Keep this window open. Copy the operator code into http://127.0.0.1:8787'
try {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m silvertrap serve --seed
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m silvertrap serve --seed
    } else {
        throw 'Python 3.11 or newer is required. Install Python, then run this file again.'
    }
    if ($LASTEXITCODE -ne 0) { throw "SilverTrap exited with code $LASTEXITCODE" }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
