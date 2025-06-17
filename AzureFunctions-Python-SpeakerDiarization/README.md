# Azure Functions Python Speaker Diarization

Azure Speech Servicesを使用した音声文字起こしと話者分離機能を提供するAzure Functionsアプリケーションです。

## ディレクトリ構成

```
AzureFunctions-Python-SpeakerDiarization/
│
├── function_app.py              ← EventGridトリガー処理
├── requirements.txt             ← Azure Functions用依存関係
├── requirements-func.txt        ← Azure Functions用依存関係（詳細版）
│
├── openai_processing/           ← OpenAI関連処理を隔離
│   ├── __init__.py
│   ├── openai_completion_core.py
│   ├── openai_completion_step1.py
│   ├── openai_completion_step2.py
│   ├── openai_completion_step3.py
│   ├── openai_completion_step4.py
│   ├── openai_completion_step5.py
│   ├── openai_completion_step6.py
│   └── requirements.txt         ← OpenAI処理用依存関係
│
├── test_openai_pipeline.py      ← OpenAIのみのテスト用スクリプト
├── host.json                    ← Azure Functions設定
├── local.settings.json          ← ローカル開発用設定
└── local.settings.template.json ← 設定テンプレート
```

## セットアップ

### 1. Azure Functions用の依存関係をインストール

```bash
pip install -r requirements.txt
```

### 2. OpenAI処理用の依存関係をインストール（必要に応じて）

```bash
cd openai_processing
pip install -r requirements.txt
cd ..
```

### 3. 環境変数の設定

`local.settings.json`を`local.settings.template.json`を参考に作成し、必要な環境変数を設定してください。

### 4. Azure Functionsの起動

```bash
func start
```

## 機能

### EventGridトリガー（TriggerTranscriptionJob）
- Blobストレージへの音声ファイルアップロードを検知
- Azure Speech Servicesで非同期文字起こしジョブを作成
- 話者分離機能付きで文字起こしを実行

### HTTPトリガー（TranscriptionCallback）
- Azure Speech Servicesからの文字起こし完了通知を受信
- 文字起こし結果をデータベースに保存
- OpenAI APIを使用した会話の自動整形処理

## テスト

### OpenAI処理のテスト

```bash
# meeting_id指定でテスト
python test_openai_pipeline.py --meeting-id 123

# 直接テキストでテスト
python test_openai_pipeline.py --text "Speaker1: こんにちは\nSpeaker2: はい"
```

## 依存関係の分離

このプロジェクトでは、依存関係を以下のように分離しています：

- **Azure Functions用**: `requirements.txt` / `requirements-func.txt`
  - Azure Functions、Azure Speech Services、データベース接続など

- **OpenAI処理用**: `openai_processing/requirements.txt`
  - OpenAI API、日本語テキスト処理、データ処理など

これにより、各機能に必要な依存関係のみをインストールでき、依存関係の競合を避けることができます。 