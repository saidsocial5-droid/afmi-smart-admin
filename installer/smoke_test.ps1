# Test de fumée du logiciel construit (build\app) : démarre le backend Smart Office compilé sur la base de démonstration,
# vérifie l'API, les types MIME de l'interface, puis affiche la page dans un navigateur (erreurs JavaScript, capture).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "build\smoke"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$work = Join-Path $env:TEMP "afmi-smoke"
Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
Copy-Item -Recurse (Join-Path $root "build\app\demo") $work
$env:AFMI_DESKTOP_DB = Join-Path $work "database.db"
$env:AFMI_DATA_DIR = Join-Path $work "data"
$env:AFMI_API_TOKEN = "jeton-de-test"
$env:AFMI_DISABLE_SCHEDULER = "1"
$env:PYTHONUTF8 = "1"
$exe = Join-Path $root "build\app\SmartOffice\smartoffice-backend\smartoffice-backend.exe"
$proc = Start-Process -FilePath $exe -ArgumentList "--port", "8765" -PassThru -NoNewWindow `
    -RedirectStandardOutput (Join-Path $out "backend.out.txt") -RedirectStandardError (Join-Path $out "backend.err.txt")
$headers = @{ "X-AFMI-Token" = "jeton-de-test" }
$ok = $false
for ($i = 0; $i -lt 90; $i++) {
    if ($proc.HasExited) { break }
    try { Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/agents" -Headers $headers -TimeoutSec 5 | Out-Null; $ok = $true; break } catch { Start-Sleep -Seconds 1 }
}
try {
    if (-not $ok) { throw "Le backend compilé ne répond pas (voir backend.err.txt)." }
    foreach ($path in "/api/settings/header", "/api/exports/engines", "/api/settings/registry", "/api/ged/documents", "/api/statements/context") {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8765$path" -Headers $headers -UseBasicParsing
        Write-Host "$path -> $($r.StatusCode)"
    }
    $index = Invoke-WebRequest -Uri "http://127.0.0.1:8765/" -Headers $headers -UseBasicParsing
    $script = [regex]::Match($index.Content, 'src="\.?(/assets/[^"]+\.js)"').Groups[1].Value
    if (-not $script) { throw "Aucun script trouvé dans la page d'accueil." }
    $js = Invoke-WebRequest -Uri "http://127.0.0.1:8765$script" -Headers $headers -UseBasicParsing
    Write-Host "Type du script $script : $($js.Headers['Content-Type'])"
    if ($js.Headers['Content-Type'] -notmatch "javascript") { throw "Script servi avec le type $($js.Headers['Content-Type'])." }
    Push-Location $out
    npm init -y | Out-Null
    npm install --silent playwright@1.48.2 | Out-Null
    npx playwright install chromium | Out-Null
    node (Join-Path $root "installer\smoke_page.cjs") "http://127.0.0.1:8765/?afmi_token=jeton-de-test" $out
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { throw "L'interface Smart Office ne s'affiche pas (voir smart_office.png)." }
    Write-Host "[OK] Smart Office s'affiche et répond."
}
finally {
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Get-Content (Join-Path $out "backend.err.txt") -Tail 40 -ErrorAction SilentlyContinue
}
