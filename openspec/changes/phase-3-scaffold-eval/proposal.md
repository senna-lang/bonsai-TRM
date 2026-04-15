## Why

Phase 2 で実装したスキャフォールドの効果を定量的に測定する。Phase 1 と同一タスクセット・同一評価ハーネスで実行し、Before/After の比較を行う。失敗モード分布の変化(unmasking 効果)も分析する。

## What Changes

- Phase 1 と同一スコープでスキャフォールド版評価を実行
- ベースラインとの比較分析(達成率、失敗モード分布)
- Ablation Study: Corrector のみ vs 3 役全部(時間が許せば)

## Capabilities

### New Capabilities

- `comparative-analysis`: ベースラインとスキャフォールドの結果を比較し、改善幅と統計的有意性を報告

### Modified Capabilities

- `evaluation-harness`: Phase 1 のハーネスをスキャフォールド版エージェントで再利用

## Impact

- Colab 利用時間: ベースラインの 2-3 倍(3 役呼び出し分)
- この Phase の結果が記事(Phase 4)の方向性を決定する
