## Context

McClendon et al. (2026) の 3 役スキャフォールド手法を Bonsai-8B で検証するには、まず推論サーバーと AppWorld ベンチマークの統合が必要。Bonsai-8B は Qwen3-8B ベースの 1-bit LLM (1.15GB) であり、CUDA 環境での動作は未検証。bonsai-bankai プロジェクトで M2 Mac + MLX での動作は確認済み(モデルロード 1.2 秒、30 tokens/1.7 秒)。

## Goals / Non-Goals

**Goals:**
- Colab Pro (A100/V100) で Bonsai-8B GGUF が推論できることを確認
- AppWorld をインストールし、ダミーエージェントでタスクが動くことを確認
- Bonsai を AppWorld エージェントの LLM バックエンドとして接続
- 5-10 タスクの実測で本格評価のスコープを決定

**Non-Goals:**
- スキャフォールドの実装(Phase 2)
- 全タスクのベースライン評価(Phase 1)
- 記事執筆(Phase 4)
- Qwen3-8B AWQ の再現実験

## Decisions

### 1. 推論サーバーは PrismML フォーク llama.cpp + GGUF を第一候補とする
**選択**: PrismML フォーク (`PrismML-Eng/llama.cpp`) の CUDA ビルドで `prism-ml/Bonsai-8B-gguf` (Q1_0_g128) を起動
**理由**: 上流 llama.cpp は Q1_0_g128 を**サポートしていない**（調査確定済み）。PrismML フォークが Q1_0 用 dequantization カーネルを持つ唯一の選択肢。OpenAI 互換 API サーバーモードあり。
**リスク**: PrismML フォークの CUDA ビルドが Colab 環境でコンパイルできない可能性
**フォールバック順序**:
1. Mintplex-Labs/prism-ml-llama.cpp（コミュニティフォーク、より新しい上流にリベース済み）
2. lilyanatia/Bonsai-8B-requantized（再量子化版 GGUF、上流 llama.cpp で動くが真の 1-bit ではない）
3. MLX ローカル（bonsai-bankai で動作実証済み、確実に動く）

### 2. AppWorld の simplified_react_code_agent をベースにする
**選択**: AppWorld 同梱の `simplified_react_code_agent` の LLM 呼び出し部分を Bonsai API に差し替え
**理由**: 論文の公式リポジトリも AppWorld の標準エージェントをベースにしている。最小限の変更で Bonsai と統合できる。

### 3. Phase 0 は 5-10 タスク(難易度 1)で判断する
**選択**: AppWorld の難易度 1 タスクから 5-10 個を選んで実測
**理由**: 難易度 1 は最も簡単なタスクで、Bonsai の最低限の能力を測るのに適切。全タスクを回す前に go/no-go を判断する。

### 4. Google Drive にデータを永続化する
**選択**: 評価結果・ログ・設定を Google Drive に保存
**理由**: Colab セッションは最大 24 時間で切れる。Drive 保存で結果の永続化と再開を保証。

## Risks / Trade-offs

- **[PrismML フォーク llama.cpp の CUDA ビルド失敗]** → PrismML フォークが Colab の CUDA ツールチェインでビルドできない可能性。対策: Mintplex コミュニティフォーク → 再量子化版 GGUF → MLX の順でフォールバック。**注意**: 再量子化版を使う場合は真の 1-bit ではなくなるため、記事での記述に影響する
- **[AppWorld のセットアップが複雑]** → `appworld install` / `appworld download data` が Colab 環境で失敗する可能性。対策: 公式ドキュメントに従い、問題発生時は issue 確認
- **[Bonsai が全タスクで完走しない]** → エラー停止する場合はプロンプトフォーマットの問題か能力限界かを切り分ける必要あり
- **[推論が極端に遅い]** → 1 タスク 30 分超なら 168 タスク完走が非現実的。対策: スコープ縮小
