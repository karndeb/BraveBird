FROM vllm/vllm-openai:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY server.py /app/server.py
COPY model_wrapper.py /app/model_wrapper.py

# Set multiprocessing start method for vLLM compatibility
ENV VLLM_WORKER_MULTIPROC_METHOD=spawn

# Weights mounted at /root/.cache/huggingface usually, 
# or custom path via volume
ENV MODEL_PATH="Qwen/Qwen2.5-VL-7B-Instruct"

EXPOSE 8001

CMD ["python3", "server.py"]