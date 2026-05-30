# release.ps1 - Compila Vita, empaqueta el instalador y publica una release en GitHub.
#
# Flujo para sacar una version nueva:
#   1. Sube el numero en app\__init__.py  ->  APP_VERSION = "1.0.1"
#   2. Ejecuta:  .\release.ps1
#      (o  .\release.ps1 -DryRun  para solo compilar y empaquetar, sin publicar)
#
# Requiere: py -3.12 con PyInstaller, y gh CLI autenticado (gh auth login).

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# gh CLI: usar el del PATH o, si no esta, la ruta de instalacion por defecto
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) { $gh = "C:\Program Files\GitHub CLI\gh.exe" }
if (-not (Test-Path $gh)) { throw "No encuentro gh CLI. Instala GitHub CLI o ajusta la ruta." }

# 1. Leer APP_VERSION de app\__init__.py
$initPath = Join-Path $root "app\__init__.py"
$verMatch = Select-String -Path $initPath -Pattern 'APP_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $verMatch) { throw "No encuentro APP_VERSION en app\__init__.py" }
$version = $verMatch.Matches[0].Groups[1].Value
$tag = "v$version"
Write-Host "==> Vita $tag" -ForegroundColor Cyan

# 2. Cerrar procesos que puedan bloquear los .exe
Get-Process Vita, "Instalar Vita" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 3. Compilar app e instalador
Write-Host "==> Compilando Vita.exe..." -ForegroundColor Cyan
py -3.12 -m PyInstaller Vita.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "Fallo compilando Vita.exe" }

Write-Host "==> Compilando el instalador..." -ForegroundColor Cyan
py -3.12 -m PyInstaller "Instalar Vita.spec" --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "Fallo compilando el instalador" }

# 4. Empaquetar Vita-Instalador.zip (instalador + app + LEEME)
Write-Host "==> Empaquetando Vita-Instalador.zip..." -ForegroundColor Cyan
$stage = Join-Path $root "Vita-Instalador"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item "dist\Vita.exe" $stage
Copy-Item "dist\Instalar Vita.exe" $stage
Copy-Item "installer\LEEME.txt" $stage
$zip = Join-Path $root "Vita-Instalador.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path "$stage\*" -DestinationPath $zip

# 5. Sincronizar version.json (el manifiesto que lee la app para detectar updates)
$manifest = Join-Path $root "version.json"
if (Test-Path $manifest) {
    $json = Get-Content $manifest -Raw | ConvertFrom-Json
    $json.version = $version
    # UTF-8 sin BOM (json.loads de Python no admite BOM)
    [System.IO.File]::WriteAllText($manifest, ($json | ConvertTo-Json -Depth 5))
} else {
    Write-Host "AVISO: no existe version.json todavia." -ForegroundColor Yellow
}

if ($DryRun) {
    Write-Host "DryRun: compilado y empaquetado, sin publicar." -ForegroundColor Yellow
    exit 0
}

# 6. Commit + push del manifiesto/codigo (si hay cambios)
if (-not (git config user.email)) {
    git config user.name "David Rodriguez"
    git config user.email "176689788+DavidRdgzz@users.noreply.github.com"
}
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m "Release $tag" }
git push

# 7. Publicar la release con los binarios como assets
Write-Host "==> Creando release $tag en GitHub..." -ForegroundColor Cyan
& $gh release create $tag "dist\Vita.exe" "Vita-Instalador.zip" --title "Vita $tag" --notes "Actualizacion de Vita $tag"
if ($LASTEXITCODE -ne 0) { throw "Fallo creando la release" }

Write-Host "LISTO: Vita $tag publicada. La app de tu novia detectara la actualizacion." -ForegroundColor Green
