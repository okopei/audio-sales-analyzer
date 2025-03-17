# システム要件

## アーキテクチャ
- フロントエンド: Next.js（Vercelにデプロイ）
  - ユーザーからの音声入力を取得
  - 音声データをバイナリとして取得
  - バックエンドAPIにデータを送信

- バックエンド: Python FastAPI（Azure Functionsにデプロイ予定）
  - 音声データの受信
  - Azure Speech Servicesへの中継
  - レスポンスの整形と返送
  - （必要に応じて）Azure Cosmos DBへのデータ保存

- Azure Services
  - Speech Services: 音声認識処理
  - Cosmos DB: データ保存
  - Blob Storage: 必要に応じて音声ファイルの保存

## 環境要件
- Python 3.11以上
- Node.js 18以上

## Python依存関係
- fastapi
- uvicorn（開発環境のみ）
- python-multipart
- azure-cognitiveservices-speech（音声認識用）
- azure-storage-blob（ファイル保存用）
- azure-cosmos（データベース用）
- その他必要なパッケージは requirements.txt に記載

## Node.js依存関係
- Next.js 14以上
- その他必要なパッケージは package.json に記載

## 必要なAzureサービス
- Azure Functions（バックエンド用）
- Azure Speech Services（音声認識用）
- Azure Cosmos DB（データベース）
- Azure Blob Storage（音声ファイル保存用）

## セットアップ手順
1. Azure環境のセットアップ
   - 必要なAzureサービスを作成
   - 各サービスの接続情報を環境変数として設定

2. Python環境のセットアップ
   ```bash
   cd python-api
   python -m venv venv
   source venv/Scripts/activate  # Windowsの場合
   pip install -r requirements.txt
   ```

3. Node.js環境のセットアップ
   ```bash
   cd next-app
   npm install
   ```

## 開発サーバーの起動
1. Pythonサーバー（ローカル開発用）
   ```bash
   cd python-api
   source venv/Scripts/activate
   uvicorn main:app --reload
   ```

2. Next.jsサーバー
   ```bash
   cd next-app
   npm run dev
   ```

## デプロイ
1. フロントエンド
   - GitHubリポジトリをVercelと連携
   - 環境変数の設定
   - 自動デプロイの設定

2. バックエンド
   - Azure Functionsへのデプロイ
   - 環境変数の設定
   - CORSの設定

## 注意事項
- ローカルマシンに依存するライブラリは使用しない
- FFmpegなどのシステムライブラリに依存する機能は、クラウドサービスで代替
- 音声認識はAzure Speech Servicesを使用
- 環境変数は.env.localで管理（本番環境ではVercelとAzureの環境変数で管理）

## アーキテクチャの利点
1. Vercelでのデプロイが容易（ローカル依存がない）
2. スケーラブルな構成
3. マネージドサービスの活用でインフラ管理が最小限
4. サーバーレスアーキテクチャによるコスト最適化

## 開発状況
- 現在は開発初期段階
- Next.js ⇔ Python APIの基本的な通信部分を実装済み
- 次のステップはAzureサービスとの連携実装 