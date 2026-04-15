## 1. 論文 Method セクションの精読と設計

- [ ] 1.1 論文 p.5-7 (Three-Tier Inference Scaffolding) を精読し、各 Tier の入出力仕様を整理
- [ ] 1.2 Figure 1 のデータフロー (observation → Summarizer → Agent → Corrector → AppWorld) を実装設計に落とす
- [ ] 1.3 Corrector の入力仕様を確認: `(a_t, d_t)` のみ、履歴 h_t へのアクセスなし (Eq. 3)
- [ ] 1.4 Summarizer の仕様を確認: N-first + K-last 保持、中間を要約、アーティファクト保持ルール
- [ ] 1.5 Phase 0/1 の実測に基づいて Bonsai 用パラメータを最終決定 (N, K, 閾値)

## 2. Step 1: Corrector 実装

- [ ] 2.1 Corrector のシステムプロンプトを作成 (論文 p.7 の要件に基づく):
  - 入力: Agent の提案コード + API ドキュメント + 直前の実行結果 (失敗時のみ)
  - 出力: 修正済みコード (1 コードブロック、apis.* 呼び出し必須)
  - 指示: エラー分類 → 診断 → 修正コード生成
  - 不確実な場合: `apis.api_docs.show_api_doc(...)` でドキュメント参照
- [ ] 2.2 Agent → Corrector → AppWorld の 2 段パイプラインを実装
- [ ] 2.3 パースエラー時のフォールバック実装 (Corrector 出力が不正なら Agent 出力をそのまま使用)
- [ ] 2.4 1 タスクで end-to-end テスト (Corrector のみ)

## 3. Step 2: Summarizer 実装

- [ ] 3.1 Summarizer のシステムプロンプトを作成 (論文 p.7 の要件に基づく):
  - 保持すべきアーティファクト: 認証トークン、API エンドポイント名とスキーマ、エラーパターンと解決策、ページネーション状態、タスク完了状況
  - 抽出済みアーティファクト (access tokens, API outputs) は verbatim で返す
- [ ] 3.2 履歴長監視: 文字数 (12,000) とトークン数 (3,000) の二重閾値で判定
- [ ] 3.3 N-first + K-last メッセージ保持ロジック (初期値 N=13, K=3)
- [ ] 3.4 Summarizer → Agent → Corrector の 3 段パイプラインに統合

## 4. Step 3: 統合テスト

- [ ] 4.1 1-2 タスクで 3 段パイプラインの end-to-end テスト
- [ ] 4.2 各ロールの呼び出しログを確認 (どの Tier がいつ呼ばれたか)
- [ ] 4.3 Summarizer のトリガー条件が適切に発動するか確認 (短いタスクでは発動しないこと)
- [ ] 4.4 推論時間の計測 (ベースライン比で何倍か)
- [ ] 4.5 Corrector の修正が実際にコードを改善しているかログで確認
