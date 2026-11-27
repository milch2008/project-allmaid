@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== Maid-chan: criando o executavel =====

if not exist "venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  python -m venv venv
)
if not exist "venv\Scripts\python.exe" (
  py -m venv venv
)
if not exist "venv\Scripts\python.exe" (
  echo ERRO: nao achei o Python. Instale em python.org marcando "Add Python to PATH".
  pause
  exit /b 1
)

echo Instalando bibliotecas...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo ERRO ao instalar as bibliotecas.
  pause
  exit /b 1
)

echo Gerando o MaidChan.exe (leva alguns minutos)...
venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --noconsole --name MaidChan --collect-all customtkinter main.py
if errorlevel 1 (
  echo ERRO ao gerar o executavel.
  pause
  exit /b 1
)

if not exist "dist\assets" mkdir "dist\assets"
xcopy /E /I /Y "assets" "dist\assets" >nul
copy /Y "apps.json" "dist\apps.json" >nul
if not exist "dist\.env" copy ".env.example" "dist\.env" >nul

echo.
echo ===== PRONTO! =====
echo Pasta: %cd%\dist
echo 1) Abra dist\.env no Bloco de Notas e cole sua chave da Groq.
echo 2) Coloque o PNG dela em dist\assets\maid_chan.png
echo 3) De dois cliques em dist\MaidChan.exe
pause
