# Prépare les composants tiers embarqués dans l'installateur AFMI Smart Admin 2.0 (à lancer une fois, sous Windows) :
#   third_party\tesseract\  : Tesseract OCR 5 (UB Mannheim, licence Apache 2.0) + langues fra et ara (tessdata, Apache 2.0)
#   third_party\fonts\      : police arabe Amiri (SIL Open Font License 1.1), utilisée par les rapports en arabe
# Chaque fichier téléchargé est consigné avec son empreinte SHA-256 dans third_party\SHA256SUMS.txt. Aux constructions
# suivantes, les empreintes sont vérifiées : un fichier modifié arrête la construction.
param(
    [string]$TesseractInstaller = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe",
    [string]$TessdataBase = "https://github.com/tesseract-ocr/tessdata/raw/main",
    [string]$FontBase = "https://github.com/google/fonts/raw/main/ofl/amiri"
)
$ErrorActionPreference = "Stop"
$root = Join-Path (Split-Path -Parent $PSScriptRoot) "third_party"
$downloads = Join-Path $root "downloads"
$sums = Join-Path $root "SHA256SUMS.txt"
New-Item -ItemType Directory -Force -Path $downloads, (Join-Path $root "fonts") | Out-Null

$known = @{}
if (Test-Path $sums) { Get-Content $sums | ForEach-Object { $p = $_ -split "  ", 2; if ($p.Count -eq 2) { $known[$p[1]] = $p[0] } } }

function Get-Verified([string]$url, [string]$target) {
    $name = Split-Path -Leaf $target
    if (-not (Test-Path $target)) {
        Write-Host "Téléchargement de $name..."
        Invoke-WebRequest -Uri $url -OutFile $target -UseBasicParsing
    }
    $hash = (Get-FileHash -Algorithm SHA256 $target).Hash.ToLower()
    if ($known.ContainsKey($name)) {
        if ($known[$name] -ne $hash) { throw "Empreinte inattendue pour $name : $hash (attendue $($known[$name]))." }
    } else {
        Add-Content -Path $sums -Value "$hash  $name"
        $known[$name] = $hash
        Write-Host "  nouvelle empreinte consignée : $hash — à contrôler avec la source officielle."
    }
}

# 1. Tesseract (installation silencieuse dans third_party\tesseract, sans toucher au système)
$setup = Join-Path $downloads (Split-Path -Leaf $TesseractInstaller)
Get-Verified $TesseractInstaller $setup
$tess = Join-Path $root "tesseract"
if (-not (Test-Path (Join-Path $tess "tesseract.exe"))) {
    Start-Process -FilePath $setup -ArgumentList "/S", "/D=$tess" -Wait
    if (-not (Test-Path (Join-Path $tess "tesseract.exe"))) { throw "Installation de Tesseract dans $tess impossible." }
}
foreach ($lang in "fra", "ara") {
    Get-Verified "$TessdataBase/$lang.traineddata" (Join-Path $downloads "$lang.traineddata")
    Copy-Item (Join-Path $downloads "$lang.traineddata") (Join-Path $tess "tessdata\$lang.traineddata") -Force
}

# 2. Police arabe Amiri
foreach ($f in "Amiri-Regular.ttf", "Amiri-Bold.ttf", "OFL.txt") {
    Get-Verified "$FontBase/$f" (Join-Path $downloads $f)
    Copy-Item (Join-Path $downloads $f) (Join-Path $root "fonts\$f") -Force
}
& (Join-Path $tess "tesseract.exe") --list-langs
Write-Host "[OK] Composants tiers prêts dans $root"
