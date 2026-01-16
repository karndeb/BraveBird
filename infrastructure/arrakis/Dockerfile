# Base image: Ubuntu 22.04 (LTS)
FROM ubuntu:22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install System Dependencies
# - xfce4: Lightweight Desktop Environment
# - tigervnc: For visual observation
# - chromium-browser: For web browsing tasks
# - python3: For Coding Agent execution
# - xdotool: For injecting mouse/keyboard events programmatically
RUN apt-get update && apt-get install -y \
    xfce4 \
    xfce4-terminal \
    tigervnc-standalone-server \
    chromium-browser \
    python3 \
    python3-pip \
    python3-tk \
    python3-dev \
    xdotool \
    scrot \
    net-tools \
    curl \
    vim \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Data Science / Agent Libraries
# Pre-installing these speeds up the Coding Agent significantly
RUN pip3 install --no-cache-dir \
    pandas \
    numpy \
    matplotlib \
    openpyxl \
    beautifulsoup4 \
    requests \
    lxml \
    pillow \
    playwright

# Install Playwright browsers
RUN playwright install chromium

# 3. Configure VNC (The "Eyes" Port)
# No password for local sandbox isolation
RUN mkdir -p /root/.vnc \
    && echo "#!/bin/sh\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nstartxfce4 &" > /root/.vnc/xstartup \
    && chmod +x /root/.vnc/xstartup

# 4. Setup Workspace
WORKDIR /workspace

# 5. Startup Script
# Starts VNC server and keeps the container alive
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

CMD ["/usr/local/bin/start.sh"]