# ============================================================
# start-frontend.ps1 - Arranca el frontend de AI-NOC Copilot
# ============================================================

$ProjectRoot = "D:\AiProject\ai-noc-copilot"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackendDir  = Join-Path $ProjectRoot "backend"

Write-Host "🎨 Iniciando Frontend (Streamlit)..." -ForegroundColor Cyan

# Cambiar a la carpeta del frontend
Set-Location $FrontendDir

# Activar el mismo entorno virtual del backend
& "$BackendDir\.venv\Scripts\Activate.ps1"

# Verificar que streamlit esté instalado
$streamlitInstalled = Get-Command streamlit -ErrorAction SilentlyContinue
if (-not $streamlitInstalled) {
    Write-Host "📦 Streamlit no está instalado. Instalando..." -ForegroundColor Yellow
    pip install streamlit httpx
}

# Cargar variables de entorno desde .env si existe
if (Test-Path ".env") {
    Write-Host "📂 Cargando variables de entorno desde .env..." -ForegroundColor Yellow
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Establecer variable por defecto si no está en .env
if (-not $env:BACKEND_URL) { $env:BACKEND_URL = "http://localhost:8000" }

Write-Host ""
Write-Host "⚙️  Configuración:" -ForegroundColor Cyan
Write-Host "   BACKEND_URL = $env:BACKEND_URL"
Write-Host ""
Write-Host "🎨 Arrancando dashboard en http://localhost:8501..." -ForegroundColor Green
Write-Host "   (Presiona Ctrl+C para detener)" -ForegroundColor Gray
Write-Host ""

# Arrancar Streamlit
streamlit run dashboard.py --server.port 8501 --server.headless false