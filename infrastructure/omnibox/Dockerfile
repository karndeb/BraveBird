# Use the stable, pre-built Windows-in-Docker image
FROM dockurr/windows:latest

# Metadata
LABEL app="Bravebird-OmniBox"
LABEL description="Windows 11 Sandbox with Bravebird Agent pre-loaded"

# --- Configuration ---
# These match the settings required for decent performance
ENV VERSION="11"
ENV RAM_SIZE="8G"
ENV CPU_CORES="4"
ENV DISK_SIZE="64G"

# --- Network ---
# 8006 = NoVNC (Visual View)
# 5000 = Agent API (Our Bridge)
EXPOSE 8006 5000

# --- Injection ---
# The 'dockurr' image looks at the /custom/ folder to run scripts on first boot.
# We copy our agent code and bootstrap script there.

# 1. Create the custom directory
RUN mkdir -p /custom

# 2. Copy the Bootstrap Script (The "Installer")
# This runs automatically when Windows boots for the first time
COPY scripts/bootstrap_agent.bat /custom/install.bat

# 3. Copy the Agent Server Code
# The bootstrap script will move this from the ISO mount to C:\Bravebird\
COPY server/main.py /custom/win_agent_server.py
COPY server/cursor.png /custom/cursor.png
COPY requirements.txt /custom/requirements.txt

# --- Storage ---
# Persist the C: drive so we don't reinstall Windows every time
VOLUME ["/storage"]
