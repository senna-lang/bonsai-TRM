#!/bin/bash
# RunPod セットアップスクリプト
# 使い方: bash setup_runpod.sh

set -e

echo "=== 1. 依存インストール ==="
pip install -q "pydantic==1.10.26" "fastapi==0.110.3"
pip install -q appworld huggingface_hub openai tiktoken

echo "=== 2. AppWorld セットアップ ==="
cd /workspace
appworld install
appworld download data

echo "=== 3. Bonsai-8B GGUF ダウンロード ==="
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(repo_id='prism-ml/Bonsai-8B-gguf', filename='Bonsai-8B.gguf', local_dir='/workspace/model')
print('Model downloaded')
"

echo "=== 4. PrismML fork llama.cpp ビルド ==="
if [ ! -f /workspace/llama-cpp-prism/build/bin/llama-server ]; then
    git clone https://github.com/PrismML-Eng/llama.cpp /workspace/llama-cpp-prism
    cd /workspace/llama-cpp-prism
    cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native
    cmake --build build --config Release -j$(nproc)
    cd /workspace
else
    echo "Already built"
fi

echo "=== 5. 推論サーバー起動 ==="
pkill -9 -f llama-server 2>/dev/null || true
sleep 2

/workspace/llama-cpp-prism/build/bin/llama-server \
    -m /workspace/model/Bonsai-8B.gguf \
    --host 0.0.0.0 \
    --port 8090 \
    -ngl 99 \
    -c 16384 \
    > /workspace/server.log 2>&1 &

echo "Waiting for server..."
sleep 20

if curl -s http://localhost:8090/health > /dev/null; then
    echo "Server OK"
else
    echo "Server FAILED"
    tail -20 /workspace/server.log
    exit 1
fi

echo "=== Setup complete ==="
echo "Run: python3 /workspace/bonsai-TRM/scripts/run_scaffold.py"
