@echo off
setlocal EnableDelayedExpansion
REM =====================================================================
REM  SISTEMA DE AUTOMACAO DE SINISTROS AON - EXECUTOR PRINCIPAL
REM =====================================================================
REM  Este script executa o sistema de automacao com verificacoes completas
REM  e tratamento de erros detalhado.
REM =====================================================================

REM Garante que o diretório atual é a pasta onde está este .bat
pushd "%~dp0"

REM Configurar codificação para caracteres especiais
chcp 65001 >nul 2>&1

echo.
echo =====================================================================
echo    SISTEMA DE AUTOMACAO DE SINISTROS AON - V2.0
echo    Modo: Emails das ultimas 24h DA CAIXA DE ENVIADOS
echo =====================================================================
echo    Data/Hora: %date% %time%
echo    Diretorio: %cd%
echo =====================================================================
echo.

REM ===== VERIFICACOES PREVIAS =====
echo [VERIFICACAO] Checando pre-requisitos...
echo.

REM 1. Verificar se Python está instalado
echo [1/5] Verificando instalacao do Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [❌ ERRO CRITICO] Python nao encontrado no PATH!
    echo.
    echo ► SOLUCAO:
    echo   1. Instale o Python 3.12+ em: https://www.python.org/downloads/
    echo   2. Durante a instalacao, marque "Add Python to PATH"
    echo   3. Reinicie o prompt de comando apos a instalacao
    echo.
    goto :erro_final
)
for /f %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   ✅ %PYTHON_VERSION% encontrado
echo.

REM 2. Verificar arquivo .env
echo [2/5] Verificando arquivo de configuracao (.env)...
if not exist ".env" (
    echo [❌ ERRO CRITICO] Arquivo .env nao encontrado!
    echo.
    echo ► ARQUIVO NECESSARIO: .env
    echo   Localizacao: %cd%\.env
    echo.
    echo ► CONTEUDO OBRIGATORIO:
    echo   AON_USERNAME=seu_usuario_aon
    echo   AON_PASSWORD=sua_senha_aon
    echo   AON_URL=https://url_do_sistema_aon.com
    echo   EMAIL_SUBJECT_LIST=["ENCERRAMENTO", "SINISTRO", "TOKIO"]
    echo   SUBJECT_TO_CODE={"ENCERRAMENTO": "ENC", "SINISTRO": "SIN"}
    echo.
    echo ► EXEMPLO DE ARQUIVO .env:
    echo   ----------------------------------------
    echo   AON_USERNAME=joao.silva
    echo   AON_PASSWORD=minhaSenha123
    echo   AON_URL=https://sistema.aon.com.br
    echo   ----------------------------------------
    echo.
    goto :erro_final
)
echo   ✅ Arquivo .env encontrado
echo.

REM 3. Verificar se core/main.py existe
echo [3/5] Verificando arquivo principal (core/main.py)...
if not exist "core\main.py" (
    echo [❌ ERRO CRITICO] Arquivo core\main.py nao encontrado!
    echo.
    echo ► ESTRUTURA ESPERADA:
    echo   %cd%\core\main.py
    echo.
    echo ► VERIFICAR:
    echo   - Voce esta executando o .bat na pasta correta?
    echo   - Os arquivos do projeto estao completos?
    echo.
    goto :erro_final
)
echo   ✅ Arquivo principal encontrado
echo.

REM 4. Verificar se services existe
echo [4/5] Verificando modulos de servico...
if not exist "services\email_service.py" (
    echo [❌ ERRO CRITICO] Modulo email_service.py nao encontrado!
    echo   Localizacao esperada: %cd%\services\email_service.py
    goto :erro_final
)
echo   ✅ Modulos de servico encontrados
echo.

REM 5. Verificar dependências básicas
echo [5/5] Verificando dependencias Python basicas...
python -c "import win32com.client; import selenium; import dotenv" >nul 2>&1
if errorlevel 1 (
    echo [⚠️  AVISO] Algumas dependencias podem estar faltando
    echo.
    echo ► INSTALAR DEPENDENCIAS:
    echo   pip install -r requirements.txt
    echo   ou
    echo   pip install pywin32 selenium python-dotenv webdriver-manager
    echo.
    echo [INFO] Tentando continuar mesmo assim...
    timeout /t 3 >nul
) else (
    echo   ✅ Dependencias basicas encontradas
)
echo.

REM ===== EXECUCAO DO SISTEMA =====
echo =====================================================================
echo [INICIANDO] Executando sistema de automacao...
echo =====================================================================
echo.

REM Registrar hora de início
for /f %%i in ('powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set HORA_INICIO=%%i
echo [INFO] Hora de inicio: %HORA_INICIO%
echo [INFO] Buscando emails DA CAIXA DE ENVIADOS das ultimas 24h...
echo [INFO] Logs serao salvos em: %cd%\logs\
echo.

REM Executar o sistema principal
python core\main.py

REM Capturar código de saída
set EXIT_CODE=%errorlevel%

REM ===== ANALISE DE RESULTADOS =====
echo.
echo =====================================================================
echo [ANALISE] Resultado da execucao
echo =====================================================================

REM Registrar hora de fim
for /f %%i in ('powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set HORA_FIM=%%i
echo [INFO] Hora de termino: %HORA_FIM%
echo.

if %EXIT_CODE% equ 0 (
    echo [✅ SUCESSO] Sistema executado com sucesso!
    echo.
    echo ► PROXIMOS PASSOS:
    echo   1. Verifique os logs em: logs\
    echo   2. Confira os emails processados em: data\processed\
    echo   3. Verifique se os sinistros foram cadastrados no sistema AON
) else (
    echo [❌ ERRO] Sistema encerrado com codigo de erro: %EXIT_CODE%
    echo.
    echo ► CODIGOS DE ERRO COMUNS:
    if %EXIT_CODE% equ 1 echo   Codigo 1: Erro geral do Python ou modulo nao encontrado
    if %EXIT_CODE% equ 2 echo   Codigo 2: Problema de sintaxe ou arquivo nao encontrado
    if %EXIT_CODE% equ 3 echo   Codigo 3: Problema de permissoes ou acesso negado
    if %EXIT_CODE% equ -1073741819 echo   Codigo -1073741819: Falha de memoria ou driver
    echo.
    echo ► DIAGNOSTICAR PROBLEMAS:
    echo   1. Verifique o ultimo log em: logs\
    echo   2. Execute: python core\main.py manualmente para ver erros
    echo   3. Verifique se o Outlook esta aberto e funcionando
    echo   4. Confirme se as credenciais no .env estao corretas
    echo   5. Teste a conexao com o sistema AON manualmente
)

echo.
echo ► ARQUIVOS DE LOG RECENTES:
for /f "skip=1" %%i in ('dir /b /o-d logs\*.log 2^>nul ^| findstr /n "^" ^| findstr "^[1-3]:"') do (
    for /f "tokens=2 delims=:" %%j in ("%%i") do echo   %%j
)
if not exist "logs\*.log" echo   Nenhum log encontrado

echo.
echo =====================================================================
popd
endlocal

echo.
echo [PRESSIONE] Qualquer tecla para fechar esta janela...
pause >nul
exit /b %EXIT_CODE%

:erro_final
echo =====================================================================
echo [❌ EXECUCAO INTERROMPIDA] Erro critico encontrado!
echo =====================================================================
echo.
echo ► SOLUCOES GERAIS:
echo   1. Leia as mensagens de erro acima com atencao
echo   2. Execute o configurar.bat para configurar o ambiente
echo   3. Verifique se todos os arquivos estao na pasta correta
echo   4. Consulte o README.md para instrucoes detalhadas
echo.
echo ► SUPORTE:
echo   - Documentacao: README.md
echo   - Logs: logs\
echo   - Email: fabricio.franca@aon.com
echo.
popd
endlocal
echo.
echo [PRESSIONE] Qualquer tecla para fechar esta janela...
pause >nul
exit /b 1