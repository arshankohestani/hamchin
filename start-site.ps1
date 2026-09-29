$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"
$npmPath = "C:\Program Files\nodejs\npm.cmd"
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

function Test-LocalUrl([string]$url) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (-not (Test-LocalUrl "http://127.0.0.1:8000/api/health")) {
    Start-Process -FilePath $pythonPath `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $backendRoot `
        -WindowStyle Hidden
}

if (-not (Test-LocalUrl "http://localhost:3000")) {
    Start-Process -FilePath $npmPath `
        -ArgumentList @("run", "dev") `
        -WorkingDirectory $frontendRoot `
        -WindowStyle Hidden
}

$siteReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 500
    if (Test-LocalUrl "http://localhost:3000") {
        $siteReady = $true
        break
    }
}

if (-not $siteReady) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("سایت در زمان مورد انتظار آماده نشد.", "هم‌چین") | Out-Null
    exit 1
}

Start-Process -FilePath $chromePath -ArgumentList @("http://localhost:3000")

