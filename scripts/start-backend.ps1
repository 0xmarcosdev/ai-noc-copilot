# ============================================================
# start-backend.ps1 - Arranca el backend de AI-NOC Copilot
# ============================================================

$ProjectRoot = "D:\AiProject\ai-noc-copilot"
$BackendDir  = Join-Path $ProjectRoot "backend"

Write-Host "🚀 Iniciando Backend (FastAPI)..." -ForegroundColor Cyan

# Cambiar a la carpeta del backend
Set-Location $BackendDir

# Activar el entorno virtual
& "$BackendDir\.venv\Scripts\Activate.ps1"

# Verificar que el venv esté activo
if ($env:VIRTUAL_ENV) {
    Write-Host "✅ Entorno virtual activado: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "❌ Error: No se pudo activar el entorno virtual" -ForegroundColor Red
    exit 1
}

# Cargar variables de entorno desde .env si existe
if (Test-Path ".env") {
    Write-Host "📂 Cargando variables de entorno desde .env..." -ForegroundColor Yellow
    Get-Content ".env.example" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Establecer variables por defecto si no están en .env
if (-not $env:OLLAMA_HOST)   { $env:OLLAMA_HOST   = "http://localhost:11434" }
if (-not $env:OLLAMA_MODEL)  { $env:OLLAMA_MODEL  = "my-qwen-3b:latest" }
if (-not $env:DB_PATH)       { $env:DB_PATH       = "./data/events.db" }
if (-not $env:SYSLOG_PORT)   { $env:SYSLOG_PORT   = "5514" }

Write-Host ""
Write-Host "⚙️  Configuración:" -ForegroundColor Cyan
Write-Host "   OLLAMA_HOST  = $env:OLLAMA_HOST"
Write-Host "   OLLAMA_MODEL = $env:OLLAMA_MODEL"
Write-Host "   DB_PATH      = $env:DB_PATH"
Write-Host "   SYSLOG_PORT  = $env:SYSLOG_PORT"
Write-Host ""
Write-Host "🔥 Arrancando servidor en http://localhost:8000..." -ForegroundColor Green
Write-Host "📚 Docs en: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "   (Presiona Ctrl+C para detener)" -ForegroundColor Gray
Write-Host ""

# Arrancar el servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000