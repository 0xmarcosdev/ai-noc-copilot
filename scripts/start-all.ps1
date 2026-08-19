# ============================================================
# start-all.ps1 - Arranca TODO el proyecto en Warp
# Abre 3 paneles: Backend, Frontend y Logs/Syslog
# ============================================================

$ProjectRoot = "D:\AiProject\ai-noc-copilot"
$ScriptsDir  = Join-Path $ProjectRoot "scripts"

Write-Host "🚀 AI-NOC Copilot - Arrancando todo el sistema..." -ForegroundColor Cyan
Write-Host ""

# Verificar que Ollama esté corriendo
try {
    $ollamaStatus = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3
    Write-Host "✅ Ollama está corriendo" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama NO está corriendo. Intentando iniciarlo..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "   Ollama iniciado en segundo plano" -ForegroundColor Green
}

Write-Host ""
Write-Host "Abriendo paneles en Warp..." -ForegroundColor Cyan
Write-Host ""

# Abrir Warp con múltiples paneles usando Warp CLI o simplemente
# lanzar nuevos procesos de PowerShell en la misma ventana de Warp
# NOTA: Warp no tiene un CLI oficial para paneles aún, así que
# abrimos nuevas pestañas/ventanas de PowerShell

# Panel 1: Backend
Write-Host "📡 Abriendo Backend..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "& '$ScriptsDir\start-backend.ps1'"

# Esperar un poco para que el backend arranque primero
Start-Sleep -Seconds 2

# Panel 2: Frontend
Write-Host "🎨 Abriendo Frontend..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "& '$ScriptsDir\start-frontend.ps1'"

Write-Host ""
Write-Host "✅ ¡Todo listo!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 URLs:" -ForegroundColor Cyan
Write-Host "   🌐 Dashboard:  http://localhost:8501"
Write-Host "   📚 API Docs:   http://localhost:8000/docs"
Write-Host "   🏥 Health:     http://localhost:8000/health"
Write-Host ""
Write-Host "💡 Tip: En Warp, usa Ctrl+D para dividir paneles si quieres" -ForegroundColor Gray
Write-Host "   ver todo en una sola ventana." -ForegroundColor Gray