#!/bin/bash
set -e

# 1. Clean up locks
rm -rf /tmp/.X* /tmp/.X11-unix

# 2. Start VNC Server (Display :1, Port 5901)
# Geometry matches our standardized AI input resolution
vncserver :1 -geometry 1920x1080 -depth 24 -localhost no -SecurityTypes None

# 3. Export Display for xdotool/apps
export DISPLAY=:1

# 4. Signal readiness (Optional: could call home)
echo "✅ Sandbox Ready. VNC on :1"

# 5. Keep alive
tail -f /dev/null