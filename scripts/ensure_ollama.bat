@echo off
REM Revisa si Ollama esta respondiendo; si no, lo levanta en una ventana
REM minimizada. Correr esto manualmente al empezar la sesion de trabajo --
REM no instala nada como servicio ni se agrega a autorun.

curl -s -o nul -w "%%{http_code}" http://localhost:11434/api/tags > "%TEMP%\ollama_status.txt"
set /p STATUS=<"%TEMP%\ollama_status.txt"
del "%TEMP%\ollama_status.txt"

if "%STATUS%"=="200" (
    echo Ollama ya esta corriendo.
) else (
    echo Ollama no responde, iniciando...
    start "Ollama" /min ollama serve
    echo Esperando a que arranque...
    timeout /t 6 /nobreak > nul
    curl -s -o nul -w "Estado tras iniciar: %%{http_code}\n" http://localhost:11434/api/tags
)