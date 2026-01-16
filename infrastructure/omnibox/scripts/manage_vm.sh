#!/bin/bash
# Manages the OmniBox Container
set -e

IMAGE_NAME="bravebird-omnibox"
CONTAINER_NAME="omnibox-win11"
STORAGE_DIR="./vm/win11storage"
ISO_DIR="./vm/win11iso"

function build() {
    echo "🔨 Building OmniBox Image..."
    docker build -t $IMAGE_NAME ../
}

function create() {
    echo "📦 Creating OmniBox Container..."
    
    # Ensure KVM permissions
    if [ ! -e /dev/kvm ]; then
        echo "❌ Error: /dev/kvm not found. Enable Nested Virtualization in WSL."
        exit 1
    fi
    sudo chmod 666 /dev/kvm

    docker run -it --rm \
        --name $CONTAINER_NAME \
        --device /dev/kvm \
        -p 8006:8006 \
        -p 5000:5000 \
        -v $(pwd)/$STORAGE_DIR:/storage \
        -v $(pwd)/$ISO_DIR/custom.iso:/custom.iso \
        --cap-add NET_ADMIN \
        --stop-timeout 120 \
        $IMAGE_NAME
}

function start() {
    echo "🚀 Starting OmniBox..."
    docker start $CONTAINER_NAME
    echo "Waiting for Agent API..."
    # Loop check for health
}

function stop() {
    echo "🛑 Stopping OmniBox..."
    docker stop $CONTAINER_NAME
}

case "$1" in
    build) build ;;
    create) create ;;
    start) start ;;
    stop) stop ;;
    *) echo "Usage: $0 {build|create|start|stop}" ;;
esac