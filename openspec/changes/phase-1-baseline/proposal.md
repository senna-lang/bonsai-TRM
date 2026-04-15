## Why

スキャフォールドの効果を測定するには、まずスキャフォールドなしの Bonsai ベースラインが必要。Phase 0 で確定したスコープ(168 / 56 / 30 タスク)で Bonsai 単体の AppWorld 成績を測定し、失敗モード分布を把握する。この結果がスキャフォールド設計(Phase 2)の指針と、最終的な Before/After 比較の基準値になる。

## What Changes

- 評価ハーネスの実装(チェックポイント機構付き)
- Phase 0 で決定したスコープでの全タスクベースライン実行
- 各タスクの LLM 入出力ログ収集
- 失敗モード分析(認証/スキーマ/ループ/推論の 4 カテゴリ)
- 推論時間統計の収集

## Capabilities

### New Capabilities

- `evaluation-harness`: チェックポイント付きの AppWorld 評価実行基盤(途中再開可能)
- `failure-analysis`: 失敗モードの分類・集計パイプライン
- `result-storage`: 評価結果・ログの構造化保存(Google Drive or ローカル)

### Modified Capabilities

- `appworld-integration`: Phase 0 で構築した統合レイヤーに評価ループとログ収集を追加

## Impact

- Colab 利用時間: 6-24 時間(スコープとGPUによる)
- ストレージ: 評価結果 JSON + ログファイル(数十 MB)
- この Phase の失敗モード分布が Phase 2 のスキャフォールド設計を決定する
