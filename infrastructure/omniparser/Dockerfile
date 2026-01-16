FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Service Code
# Note: We assume the 'util' folder from the OmniParser repo is copied here 
# during the build or mounted. For this structure, we copy the server script.
COPY server.py /app/server.py

# Weights are mounted at runtime to /app/weights to keep image small
ENV WEIGHTS_DIR="/app/weights"

EXPOSE 8000

CMD ["python", "-m", "server", "--port", "8000", "--device", "cuda"]