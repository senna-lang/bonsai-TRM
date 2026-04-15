## Why

Phase 1 のベースライン結果と失敗モード分布に基づき、論文の 3 役スキャフォールド(Summarizer / Agent / Corrector)を Bonsai-8B 用に実装する。論文の主張「小型モデルの機械的失敗は推論時の構造化で解消できる」が 1-bit LLM でも成立するかを検証するための核心フェーズ。

## What Changes

- Corrector ロールの実装(Agent 出力のコード修正・フォーマット矯正)
- Summarizer ロールの実装(履歴圧縮、閾値 3-4K トークン)
- 3 役統合オーケストレーション(Summarizer → Agent → Corrector)
- Bonsai 特有の調整(コンテキスト長制限、構造化出力の強化)

## Capabilities

### New Capabilities

- `corrector-role`: Agent の出力を履歴なしで検査・修正する Corrector(API ドキュメント参照でスキーマ修正、ループ検出)
- `summarizer-role`: 履歴が閾値(12,000文字/3,000トークン)を超えた場合に N=13 先頭 + K=3 末尾を保持しつつ圧縮する Summarizer
- `scaffold-orchestrator`: 3 役の呼び出し順序と条件分岐を管理するオーケストレーター

### Modified Capabilities

- `appworld-integration`: エージェントループをスキャフォールド版に差し替え

## Impact

- 開発期間: 5-7 日
- **参照実装なし**: 論文リポジトリ (`Aimpoint-Digital/appworld`) にスキャフォールドコードは未公開。論文 Method セクション (p.5-7) の記述から自前実装する
- 実装量は約 100-200 行（3 つのシステムプロンプト + 呼び出し制御ロジック）
- Bonsai のコンテキスト長制限(6K 超で品質劣化)に基づく閾値調整が必要
