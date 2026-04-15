## ADDED Requirements

### Requirement: Bonsai-8B GGUF loads and serves via OpenAI-compatible API
The system SHALL load Bonsai-8B GGUF (Q1_0, 1.15 GB) and expose it as an OpenAI-compatible HTTP API for LLM inference.

#### Scenario: CUDA backend (primary — PrismML fork required)
- **WHEN** PrismML fork of llama.cpp (`PrismML-Eng/llama.cpp`) is built with CUDA support on Colab Pro (A100/V100) and Bonsai-8B GGUF (Q1_0_g128) is loaded
- **THEN** the server responds to `/v1/chat/completions` requests with coherent text within 10 seconds per request
- **NOTE** upstream llama.cpp does NOT support Q1_0_g128. The PrismML fork adds custom dequantization kernels for 1-bit weights.

#### Scenario: Requantized GGUF backend (fallback 1)
- **WHEN** PrismML fork fails to build on Colab CUDA
- **THEN** the system uses `lilyanatia/Bonsai-8B-requantized` with upstream llama.cpp CUDA build. Note: this is no longer true 1-bit and must be disclosed in the article.

#### Scenario: MLX backend (fallback 2)
- **WHEN** all CUDA backends fail
- **THEN** the system falls back to M2 Mac + MLX (bonsai-bankai verified: 30 tokens/1.7s) and inference runs locally

### Requirement: Inference output matches known baseline quality
The system SHALL produce inference output comparable to bonsai-bankai's verified quality.

#### Scenario: Math probe cross-validation
- **WHEN** the same math probe inputs used in bonsai-bankai are sent to the CUDA backend
- **THEN** the outputs are semantically equivalent (not necessarily identical due to quantization differences)
