@echo off
echo [Bravebird] 🚀 Starting First-Time Setup...

:: 1. Define Paths
set AGENT_DIR=C:\Bravebird
set SOURCE_DIR=%~dp0

:: 2. Create Agent Directory
if not exist "%AGENT_DIR%" mkdir "%AGENT_DIR%"

:: 3. Copy Agent Files from the Docker Mount (CD-ROM/Custom volume) to C:
echo [Bravebird] Copying Agent Code...
copy "%SOURCE_DIR%win_agent_server.py" "%AGENT_DIR%\win_agent_server.py"
copy "%SOURCE_DIR%cursor.png" "%AGENT_DIR%\cursor.png"
copy "%SOURCE_DIR%requirements.txt" "%AGENT_DIR%\requirements.txt"

:: 4. Install Python (Silent)
echo [Bravebird] Installing Python...
:: Note: dockurr/windows might not have internet immediately. 
:: In production, you download python.exe in the Dockerfile and copy it here.
:: For now, we assume internet access.
curl -L -o python_inst.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
python_inst.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

:: 5. Install Dependencies
echo [Bravebird] Installing Pip Dependencies...
cd "%AGENT_DIR%"
pip install -r requirements.txt

:: 6. Open Firewall Port 5000
echo [Bravebird] Configuring Firewall...
netsh advfirewall firewall add rule name="BravebirdAgent" dir=in action=allow protocol=TCP localport=5000

:: 7. Setup Auto-Start (So it runs on reboot)
echo [Bravebird] Creating Startup Service...
echo start /B pythonw C:\Bravebird\win_agent_server.py > "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_agent.bat"

:: 8. Start Immediately
start /B python C:\Bravebird\win_agent_server.py

echo [Bravebird] ✅ Setup Complete. Agent Listening on Port 5000.

