## 1. Colab Pro 環境構築

- [ ] 1.1 Colab Pro 契約、notebook 作成
- [ ] 1.2 Google Drive 連携の設定(`/content/drive/MyDrive/bonsai_appworld`)
- [ ] 1.3 GPU 割り当て確認(A100 or V100)

## 2. Bonsai-8B GGUF on CUDA

- [ ] 2.1 `prism-ml/Bonsai-8B-gguf` (Q1_0_g128) を HuggingFace からダウンロード
- [ ] 2.2 PrismML フォーク llama.cpp (`PrismML-Eng/llama.cpp`) を CUDA でビルド（上流は Q1_0 未サポートのため必須）
- [ ] 2.3 Bonsai を OpenAI 互換 API として起動
- [ ] 2.4 簡単なプロンプトで応答確認(bonsai-bankai の math probe と同じ入力で比較可能)
- [ ] 2.5 [フォールバック 1] PrismML フォーク失敗時: Mintplex-Labs/prism-ml-llama.cpp を試行
- [ ] 2.6 [フォールバック 2] フォーク全滅時: `lilyanatia/Bonsai-8B-requantized`（再量子化版）+ 上流 llama.cpp
- [ ] 2.7 [フォールバック 3] CUDA 路線全滅時: MLX ローカル実行に切り替え（bonsai-bankai 実証済み）

## 3. AppWorld セットアップ

- [ ] 3.1 `pip install appworld` でインストール
- [ ] 3.2 `appworld install` と `appworld download data` でデータ取得
- [ ] 3.3 AppWorld チュートリアル実行(ダミーエージェントで 1 タスク)
- [ ] 3.4 AppWorld のタスク構造(難易度、カテゴリ)を把握

## 4. Bonsai × AppWorld 統合

- [ ] 4.1 `simplified_react_code_agent` の LLM 呼び出し部分を特定
- [ ] 4.2 LLM 呼び出しを Bonsai API に向ける
- [ ] 4.3 1 タスクで end-to-end 動作確認

## 5. パイロット評価(5-10 タスク)

- [ ] 5.1 難易度 1 から 5-10 タスクを選定
- [ ] 5.2 Bonsai ベースラインで実行
- [ ] 5.3 結果観察: 成功数、失敗パターン、推論時間、エラー停止の有無
- [ ] 5.4 結果を Drive に保存

## 6. スコープ決定

- [ ] 6.1 パイロット結果を文書化(推論時間、成功率、失敗パターン)
- [ ] 6.2 推論バックエンド最終決定(llama.cpp / vLLM / MLX)
- [ ] 6.3 Phase 1 スコープ決定: フル(168) / ミディアム(56) / ミニマム(30)
- [ ] 6.4 Phase 0 完了レポート作成
