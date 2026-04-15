## Why

Bonsai-8B に 3 役スキャフォールドを適用する前に、推論バックエンド(CUDA or MLX)と AppWorld の統合が動作することを確認し、5-10 タスクの実測で本格評価のスコープを決定する必要がある。Bonsai の基本動作(モデルロード、テキスト生成)は bonsai-bankai で確認済みだが、「CUDA 環境での動作」と「AppWorld との統合」は未検証。

## What Changes

- Colab Pro 環境での Bonsai-8B GGUF の動作確認(llama.cpp CUDA ビルド)
- AppWorld のインストールと基本動作確認
- AppWorld の `simplified_react_code_agent` の LLM 呼び出しを Bonsai に接続
- 5-10 タスク(難易度 1)の実測
- 推論バックエンド最終決定と Phase 1 スコープ決定

## Capabilities

### New Capabilities

- `inference-backend`: Bonsai-8B を OpenAI 互換 API として起動する推論サーバー環境(llama.cpp CUDA or MLX fallback)
- `appworld-integration`: AppWorld エージェントの LLM 呼び出しを Bonsai に向ける統合レイヤー
- `pilot-evaluation`: 5-10 タスクの実測と結果収集・分析の仕組み

### Modified Capabilities

(なし -- 初回セットアップのため既存 capability はない)

## Impact

- 依存: AppWorld (`pip install appworld`)、llama.cpp (CUDA build)、Bonsai-8B GGUF (`prism-ml/Bonsai-8B-gguf`)
- 環境: Colab Pro ($10/月) or M2 Mac (MLX, $0)
- この Phase の結果が Phase 1 以降のスコープ(168 / 56 / 30 タスク)を決定する
- 推論バックエンドの最終決定(llama.cpp / vLLM / MLX)もここで行う
