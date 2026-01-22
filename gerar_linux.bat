@echo off
cls
echo ======================================================
echo    GERADOR DE EXECUTAVEL LINUX - REDMINE MIGRADOR
echo ======================================================
echo.

:: [1/3] Construindo imagem Docker
echo [1/3] Construindo imagem Docker...
:: Usando underscores e apontando para o arquivo correto
docker build -t migrador_builder_linux -f Dockerfile.linux .

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha no build. Verifique se o arquivo se chama Dockerfile.linux
    pause
    exit /b
)

echo.
echo [2/3] Gerando binario Linux (aguarde)...
:: O comando abaixo usa a variavel %cd% para mapear sua pasta atual
docker run --rm -v "%cd%":/app migrador_builder_linux

echo.
echo [3/3] Organizando arquivos na pasta de distribuicao...

if not exist "Migrador_Redmine_Linux" mkdir "Migrador_Redmine_Linux"

:: Move o binario gerado e copia os arquivos de configuracao
if exist "dist\interface_gui_Linux" (
    move "dist\interface_gui_Linux" "Migrador_Redmine_Linux\"
    copy "padroes_sql.json" "Migrador_Redmine_Linux\"
    copy "equipe.json" "Migrador_Redmine_Linux\"
    echo.
    echo ======================================================
    echo   CONCLUIDO! Pasta: Migrador_Redmine_Linux
    echo ======================================================
) else (
    echo.
    echo [ERRO] O binario nao foi encontrado na pasta dist. Verifique o log do Docker.
)

pause