# EventGrid Trigger + Azure Speech Webhook テストスクリプト集

このディレクトリには、Azure Functions の EventGridTrigger 及び Speech-to-Text Webhook 処理のローカルテストを自動化するための PowerShell スクリプトが含まれています。

---

## 📁 ファイル一覧

| ファイル名 | 説明 |
|------------|------|
| `invoke_eventgrid_test.ps1` | EventGridイベント（Blob作成）を模倣してローカルFunctionにPOST |
| `get_transcription_results_url.ps1` | Azure Speech Transcription結果のchannel_0 URLを取得 |
| `invoke_webhook_test.ps1` | Webhookに模擬的にPOSTを送信してcallback処理をテスト |
| `sample-webhook.json` | Webhook POST用のサンプルデータ（結果JSON URL含む） |

---

## 🧪 使用手順

### ① EventGridトリガーのテスト実行

```powershell
.\invoke_eventgrid_test.ps1 -FileName "meeting_71_user_27_2025-04-30T02-11-30-801.webm"
```

※ ローカルの Azure Functions が 7072 ポートで起動中であることを確認してください。

### ② Azure Speech 結果URLの取得（channel_0）

```powershell
.\get_transcription_results_url.ps1 -TranscriptionId "<transcription-id>" -SpeechKey "<speech-api-key>"
```

結果として、resultsUrls.channel_0 のダウンロードURLが出力されます。

### ③ Webhookコールバック模擬送信

```powershell
.\invoke_webhook_test.ps1 -WebhookUrl "https://xxxx.ngrok-free.app/api/transcription-callback" -JsonPath "sample-webhook.json"
```

Webhook POSTのテストが完了し、Function の TranscriptionCallback が発火することを確認します。

---

## 🔧 注意点

1. **TRANSCRIPTION_CALLBACK_URL**
   - ngrok などで常に最新のものを `local.settings.json` に反映する必要があります
   - 変更時は Azure Functions の再起動が必要です

2. **テストファイル形式**
   - `.webm` / `.wav` / `.m4a` に対応したファイルを使用してください
   - ファイル名は `meeting_{id}_user_{id}_{timestamp}.{ext}` の形式を推奨

3. **ポート番号**
   - デフォルトで `7072` を使用
   - 必要に応じて `-Port` パラメータで変更可能

4. **エラーハンドリング**
   - 各スクリプトはエラー発生時に詳細なメッセージを出力
   - ステータスコードとレスポンス内容を確認して問題を特定

5. **セキュリティ**
   - `SpeechKey` は環境変数や Azure Key Vault での管理を推奨
   - テスト用のキーを使用し、本番環境のキーは使用しない

---

## 🔍 トラブルシューティング

### EventGridトリガーが発火しない場合
- Azure Functions が起動中か確認
- ポート番号（7072）が正しいか確認
- イベントデータの形式が正しいか確認

### Speech API の結果が取得できない場合
- SpeechKey が有効か確認
- TranscriptionId が正しいか確認
- リージョン（japaneast）が正しいか確認

### Webhook コールバックが失敗する場合
- ngrok の URL が有効か確認
- `local.settings.json` の `TRANSCRIPTION_CALLBACK_URL` が最新か確認
- サンプル JSON の形式が正しいか確認 