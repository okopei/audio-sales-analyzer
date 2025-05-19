# audio-sales-analyzer

## 必要要件

### 必須ツール
- Git
- Node.js 18.17.0以上
  - 役割: Next.jsアプリケーションの実行とAzuriteのインストールに必要
  - インストール: Node.jsの公式サイトから
- pnpm
  - 役割: Next.jsアプリケーションのパッケージ管理
  - インストール: `npm install -g pnpm`で実行
- Azure Functions Core Tools
  - 役割: Azure Functionsのローカル開発とデプロイをサポート
  - インストール: Azure Functions Core Toolsの公式ドキュメントを参照
- Azurite
  - 役割: ローカルでAzure Storageをエミュレート
  - インストール: npmを使用してインストール
- Python 3.12以下
  - 役割: Azure FunctionsのPythonプロジェクトの実行
  - インストール: Pythonの公式サイトから

### 推奨VS Code拡張機能
- Azure Functions: `ms-azuretools.vscode-azurefunctions`
- Python: `ms-python.python`
- ESLint: `dbaeumer.vscode-eslint`
- Prettier: `esbenp.prettier-vscode`
- Tailwind CSS IntelliSense: `bradlc.vscode-tailwindcss`

## 初回セットアップ手順

### 1. リポジトリのクローン
```bash
# 最新のDevelopブランチをクローン
git clone -b develop https://github.com/okopei/audio-sales-analyzer.git
cd audio-sales-analyzer
```

### 2. Next.jsアプリケーション（初回セットアップ）
```bash
cd next-app
npm install
cp .env.example .env.local
npm run dev
```
→ http://localhost:3000 でアクセス可能

### 3. Azure Functions環境のセットアップ

Terminal 1（Azurite起動用）:
```bash
# AzureFunctions-Python-apiディレクトリで実行
cd AzureFunctions-Python-api
azurite
```

Terminal 2（Functions起動用）:
```bash
# AzureFunctions-Python-apiディレクトリで実行
func start
```
→ http://localhost:7071/api/http_trigger でアクセス可能

Terminal 3（テスト実行用）:
```powershell
# テストリクエストの例
Invoke-RestMethod -Uri http://localhost:7071/api/http_trigger -Method Post -Headers @{"Content-Type"="application/json"} -Body '{"title": "Sample Title", "url": "http://example.com"}'
```

### データベース参照
```sql
CREATE TABLE dbo.ToDo (
    [Id] UNIQUEIDENTIFIER PRIMARY KEY,
    [order] INT NULL,
    [title] NVARCHAR(200) NOT NULL,
    [url] NVARCHAR(200) NOT NULL,
    [completed] BIT NOT NULL
);

-- データ確認用クエリ
SELECT * FROM dbo.ToDo;
```

## ローカル環境セットアップ（2回目以降）

### 1. Next.jsアプリケーション
```bash
# next-appディレクトリに移動
cd next-app

# 開発サーバー起動のみ
npm run dev
```
→ http://localhost:3000 でアクセス可能

### 2. Azure Functions環境
Terminal 1（Azurite起動用）:
```bash
# AzureFunctions-Python-apiディレクトリで実行
cd AzureFunctions-Python-api
azurite
```

Terminal 2（Functions起動用）:
```bash
# AzureFunctions-Python-apiディレクトリで実行
func start
```
→ http://localhost:7071/api/http_trigger でアクセス可能

Terminal 3（テスト実行用）:
```powershell
# テストリクエストの例
Invoke-RestMethod -Uri http://localhost:7071/api/http_trigger -Method Post -Headers @{"Content-Type"="application/json"} -Body '{"title": "Sample Title", "url": "http://example.com"}'
```

## プロジェクトドキュメント

### BACKLOG.md
- プロジェクトのタスク管理と進捗追跡用ドキュメント
- 以下の内容を記録
  - 実装予定の機能一覧
  - 優先順位とステータス
  - スプリントの計画と実績
  - バグ修正タスク

### DATABASE.md
- データベース設計と構成の管理ドキュメント
- 以下の内容を記録
  - テーブル設計とスキーマ
  - インデックス設計
  - マイグレーション履歴
  - パフォーマンスチューニング

### REQUIREMENT.md
- プロジェクトの要件定義と仕様書
- 以下の内容を記録
  - システム要件
  - デプロイメント要件

  ### KNOWLEDGE.md
- プロジェクトの技術的な知見を蓄積するドキュメント
- 以下の内容を記録
  - トラブルシューティング
  - 設計判断の記録
  - 技術的な調査結果
  - 重要な設定変更の履歴
- AIに「メモ」「記録」と指示することで、自動的にこのファイルに追記される

## 開発者ルール

### 1. 機密情報の取り扱い

#### 環境変数とシークレットの管理
- 機密情報（APIキー、接続文字列など）は`.env.local`や`local.settings.json`に保存し、Gitにコミットしない
- テンプレートファイル（`.env.template`や`local.settings.template.json`）を用意し、必要な変数名のみを記載
- 新しい環境変数を追加する場合は、テンプレートファイルも更新する

#### 初回セットアップ時の手順
1. テンプレートファイルをコピーして実際の設定ファイルを作成
   ```bash
   # Next.jsアプリ
   cp next-app/.env.template next-app/.env.local
   
   # Azure Functions API
   cp AzureFunctions-Python-api/local.settings.template.json AzureFunctions-Python-api/local.settings.json
   
   # Azure Functions SpeakerDiarization
   cp AzureFunctions-Python-SpeakerDiarization/local.settings.template.json AzureFunctions-Python-SpeakerDiarization/local.settings.json
   ```

2. 作成したファイルに実際の値を設定

#### 誤ってコミットした場合の対処法
機密情報を誤ってコミットした場合は、以下の手順で対処：

1. 該当ファイルをGitの追跡から除外
   ```bash
   git rm --cached <ファイルパス>
   ```

2. `.gitignore`に該当ファイルを追加（すでに追加されていることを確認）

3. 必要に応じて、履歴からも完全に削除（注意: 共有リポジトリの場合は他の開発者と調整が必要）
   ```bash
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch <ファイルパス>" --prune-empty --tag-name-filter cat -- --all
   ```

4. 該当する認証情報（APIキーなど）をローテーション（再発行）

### 2. Gitブランチ命名規則

#### ブランチプレフィックス
- `feature/` : 新機能開発
- `bugfix/` : バグ修正
- `hotfix/` : 緊急のバグ修正
- `release/` : リリース準備
- `docs/` : ドキュメント関連
- `test/` : テスト関連

#### 命名形式
```
<prefix>/<issue-number>-<short-description>
```

例：
- `feature/123-add-voice-upload`
- `bugfix/124-fix-search-error`
- `docs/125-update-api-docs`

### 3. コミットメッセージ規則

#### 形式
```
<type>: <subject>

<body>

<footer>
```

#### タイプ
- `feat` : 新機能
- `fix` : バグ修正
- `docs` : ドキュメントのみの変更
- `style` : コードの意味に影響を与えない変更（空白、フォーマット等）
- `refactor` : バグ修正や機能追加ではないコードの変更
- `test` : テストの追加・修正
- `chore` : ビルドプロセスやツールの変更

例：
```
feat: 音声アップロード機能の追加

- ドラッグ&ドロップによるアップロード実装
- プログレスバーの追加
- ファイルサイズのバリデーション追加

Closes #123
```

### 4. コーディング規則

#### Python（バックエンド）
- PEP 8に準拠
- 型ヒントを使用
- ドキュメンテーション文字列必須

例：
```python
def process_audio_file(file_path: str) -> dict:
    """音声ファイルを処理し、解析結果を返す

    Args:
        file_path (str): 処理する音声ファイルのパス

    Returns:
        dict: 解析結果を含む辞書
    """
    pass
```

#### TypeScript（フロントエンド）
- ESLintの設定に従う
- Prettierでフォーマット
- コンポーネントにはJSDocを記述

例：
```typescript
/**
 * 音声プレーヤーコンポーネント
 * @param {AudioPlayerProps} props - プレーヤーのプロパティ
 * @returns {JSX.Element} 音声プレーヤー
 */
const AudioPlayer: React.FC<AudioPlayerProps> = ({ url, title }) => {
  // ...
};
```

### 5. PRレビュールール

#### PRテンプレート
```markdown
## 変更内容
- 


## 特記事項

```

#### レビュー基準
- コーディング規約の遵守
- テストの網羅性
- パフォーマンスへの影響
- セキュリティ上の考慮


## Git操作のベストプラクティス

### git rebaseとは
rebaseは「ブランチの基点を変更する」操作です。mainブランチの最新の変更を取り込む際に使用します。
- mergeと異なり、履歴を直線的に保つことができる
- コンフリクトの解決が一度に必要
- プッシュ済みのブランチでは使用を避ける（チーム開発時の混乱を防ぐため）

### git stashとは
stashは「作業中の変更を一時的に退避させる」操作です。以下の場合に使用します：
- 作業途中で緊急の作業が入った時
- ブランチの切り替えが必要な時
- まだコミットしたくない変更を一時的に保存したい時

### コンフリクト回避と解決
- 作業開始前に必ずpullする
- 長期作業の場合は定期的にdevelopブランチの変更を取り込む
- develop(開発用)、main(本番用)
```bash
# mainの変更を取り込む（rebase推奨）
git checkout main
git pull
git checkout your-branch
git rebase main

# コンフリクト発生時
git rebase --continue  # コンフリクト解決後
git rebase --abort    # rebaseを中止する場合
```

### 作業の一時退避
- 作業中のコードを一時的に保存する場合はstashを使用
```bash
# 変更を一時保存
git stash save "作業の説明"

# 保存した作業の一覧確認
git stash list

# 最新のstashを復元
git stash pop

# 特定のstashを復元
git stash apply stash@{n}

# 不要なstashの削除
git stash drop stash@{n}
```

### ブランチ操作のTips
- 作業前に適切なブランチにいることを確認
```bash
# 現在のブランチ確認
git branch

# 新しいブランチを作成して切り替え
git checkout -b feature/new-branch

# 誤ったコミットを取り消し（pushする前）
git reset --soft HEAD^
```

### コミット関連
- コミット前に変更内容を確認
```bash
# 変更ファイルの確認
git status

# 変更内容の詳細確認
git diff

# 特定ファイルの変更のみコミット
git add -p
```


## トラブルシューティング

### トラブルシューティング一覧表

| エラーNo | システム | 問題 | 発生状況 | 解決方法 | 結果 | 次のステップ |
|---------|---------|------|----------|----------|------|------------|
| E008 | Azure Blob Storage | コンテナへのアクセスエラー（404） | フィードバック画面で音声ファイルの読み込みに失敗 | 1. Azure Portalで新しいSASトークンを生成<br>2. 必要な権限を設定（Read, List）<br>3. .env.localのNEXT_PUBLIC_AZURE_STORAGE_SAS_TOKENを更新<br>4. アプリケーションを再起動 | | |
| E009 | Next.js | `node_modules`に関するエラー | • パッケージの依存関係が壊れた場合<br>• `package.json`が更新された後の不整合<br>• Gitからクローンしたあとのモジュールエラー | ```bash<br># node_modulesを削除して再インストール<br>rm -rf node_modules<br>npm install<br>``` | | |
| E010 | Next.js | ビルドエラー | • TypeScriptの型エラー<br>• キャッシュの不整合<br>• 環境変数の設定ミス | ```bash<br># Next.jsのキャッシュをクリア<br>npm run clean<br><br># 必要に応じて再ビルド<br>npm run build<br>``` | | |
| E011 | Next.js | 直接URLアクセス時のルーティング問題 | • http://localhost:3000/dashboardや/manager-dashboardを直接URLに入力すると、http://localhost:3000にリダイレクトされてしまう<br>• 認証情報がある状態でも、直接URLアクセスができない | **【未解決】**<br>以下のアプローチを試したが解決しなかった：<br>• ミドルウェア（middleware.ts）を作成して認証状態の確認とルーティング制御<br>• useAuthフックの修正でローカルストレージとCookieの両方に認証情報を保存<br><br>調査が必要な点：<br>• Next.jsのルーティングの仕組みと認証状態の連携<br>• サーバーサイドでの認証状態の確認方法<br>• バージョン依存の問題の可能性 | | |
| E012 | Python | パッケージの競合 | • 異なるバージョンのパッケージが混在<br>• `requirements.txt`の更新後<br>• Python自体のバージョン不整合 | ```bash<br># 仮想環境を再作成<br>rm -rf venv<br>python -m venv venv<br>source venv/bin/activate  # または venv\Scripts\activate<br>pip install -r requirements.txt<br>``` | | |
| E013 | Python | 環境変数エラー | • `.env`ファイルが存在しない<br>• 必要な環境変数が設定されていない<br>• 環境変数の値が不正 | ```bash<br># .envファイルが存在することを確認<br>ls .env<br><br># 必要に応じて.env.exampleからコピー<br>cp .env.example .env<br><br># .envファイルの内容を確認<br>cat .env<br>``` | | |
| E014 | Python | FastAPIサーバー起動エラー | • ポート8000が既に使用されている<br>• データベース接続エラー<br>• 依存パッケージの不足 | ```bash<br># 使用中のポートを確認<br>## Windows<br>netstat -ano \| findstr :8000<br>## macOS/Linux<br>lsof -i :8000<br><br># 別のポートで起動<br>uvicorn main:app --reload --port 8001<br>``` | | |
| E015 | Git | 誤って削除したファイルの復元 | • ファイルを誤って削除した場合 | ```bash<br>git checkout -- deleted-file<br>``` | | |
| E016 | Git | コミット履歴の確認が必要 | • 変更履歴を確認したい場合<br>• 特定の変更を追跡したい場合 | ```bash<br># 詳細なログの確認<br>git log --oneline --graph<br><br># 特定ファイルの変更履歴<br>git log -p filename<br>``` | | |
| E017 | Git | ブランチの整理 | • 不要なブランチが多数ある場合 | ```bash<br># マージ済みブランチの削除<br>git branch --merged \| grep -v "\*" \| xargs -n 1 git branch -d<br>``` | | |
| E018 | Git | 改行コード問題 | • Windows環境（CRLF）とLinux/Mac環境（LF）で開発している場合<br>• 「ローカルの変更がある」というエラーが出るが、実際には変更していない場合<br>• プル/マージ時に改行コードの競合が発生する場合 | ```bash<br># 1. .gitattributesファイルを設定<br>*.py text eol=lf<br>*.js text eol=lf<br>*.jsx text eol=lf<br>*.ts text eol=lf<br>*.tsx text eol=lf<br><br># 2. 改行コードの自動変換を無効化<br>git config --global core.autocrlf false<br><br># 3. 既存の改行コード問題を解決<br>git add .<br>git commit -m "fix: 改行コード（CRLF→LF）の統一"<br>``` | | |
| E019 | Azure Functions | 接続文字列エラー | • local.settings.jsonの設定が不正<br>• 環境変数が正しく設定されていない | local.settings.jsonの`AzureWebJobsStorage`が正しく設定されているか確認 | | |
| E020 | Azure Functions | Blobアクセスエラー | • Azuriteが起動していない<br>• コンテナが存在しない | Azuriteが起動しているか、コンテナが存在するか確認 | | |
| E021 | Azure Functions | SQLエラー | • データベース接続文字列が不正<br>• テーブル構造が一致しない | データベース接続文字列とテーブル構造を確認 | | |
| E022 | Azure Functions | EventGridトリガーエラー | • イベントデータのフォーマットが不正<br>• 接続文字列の問題 | テストJSONファイルのフォーマットとAzuriteの接続文字列を確認 | | |
| E023 | Azure Functions | TranscriptionCallback関数が未実装 | 音声ファイルの文字起こし処理が実行できない | 1. Azure Speech Servicesの設定確認<br>2. TranscriptionCallback関数の実装<br>3. 文字起こし結果の保存処理の実装 | | |
| E024 | Azure Functions | 音声ファイルの文字起こし処理 | 音声ファイルのアップロード後の処理が未実装 | 1. Azure Blob Storageからの音声ファイル取得<br>2. Azure Speech Servicesによる文字起こし<br>3. 文字起こし結果のデータベース保存 | | |

# ファイル名の命名規則

## 概要
Azure Blob Storageへのファイルアップロードには2つの方法があります：
1. 音声録音によるアップロード
2. ファイル名を指定してのアップロード

## 問題点
日本語を含むファイル名を使用すると、Azure Blob Storageでのアクセスに問題が発生する可能性があります。

## 推奨されるファイル名形式
```
[タイムスタンプ13桁]_meeting_[連番3桁].wav
```
例：`1742097766757_meeting_001.wav`

## 注意事項
- ファイル名は数字と英字のみを使用することを推奨
- 日本語や特殊文字を含むファイル名は避ける
- タイムスタンプは13桁のUNIXタイムスタンプを使用
- 連番は3桁の数字を使用（001, 002, ...）

## 実装方法
1. 音声録音時：
   - 自動的に推奨形式のファイル名を生成
   - タイムスタンプと連番を自動付与

2. ファイル名指定時：
   - ファイル名を推奨形式に変換
   - 日本語や特殊文字を適切にエンコード

## トラブルシューティング
- 404エラーが発生した場合：
  1. ファイル名が正しい形式か確認
  2. 日本語や特殊文字が含まれていないか確認
  3. ファイルが正しくアップロードされているか確認

## EventGridトリガーのテスト方法

### PowerShellでのテスト実行

Azure FunctionsのEventGridトリガー（`TriggerTranscriptionJob`）をテストするには、以下のPowerShellコードを使用します：

```powershell
# EventGridイベントの構築
$event = @(
    @{
        id = [guid]::NewGuid().ToString()
        subject = "/blobServices/default/containers/moc-audio/blobs/meeting_71_user_27_2025-04-30T02-11-30-801.webm"
        eventType = "Microsoft.Storage.BlobCreated"
        eventTime = (Get-Date).ToUniversalTime().ToString("o")
        dataVersion = "1.0"
        data = @{
            api = "PutBlob"
            clientRequestId = [guid]::NewGuid().ToString()
            requestId = [guid]::NewGuid().ToString()
            eTag = "0x8DBB9715E8F04AF"
            contentType = "video/webm"
            contentLength = 123456
            blobType = "BlockBlob"
            url = "https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.webm"
            sequencer = "000000000000000000000000000000000000000000000000"
            storageDiagnostics = @{
                batchId = [guid]::NewGuid().ToString()
            }
        }
    }
) | ConvertTo-Json -Depth 10

# デバッグ用にイベントの内容を確認
Write-Host "Sending event:"
Write-Host $event

# EventGridトリガーを呼び出し
$response = Invoke-WebRequest `
    -Uri "http://localhost:7072/runtime/webhooks/eventgrid?functionName=TriggerTranscriptionJob" `
    -Method POST `
    -Headers @{
        "Content-Type" = "application/json"
        "aeg-event-type" = "Notification"  # このヘッダーが重要
    } `
    -Body $event `
    -ErrorAction Stop

Write-Host "Response status: $($response.StatusCode)"
Write-Host "Response body: $($response.Content)"
```

### 注意事項

1. 実行前に確認すること
   - Azure Functionsが実行中であること
   - ポート7072が正しいこと
   - 関数名`TriggerTranscriptionJob`が正しいこと

2. イベントの形式
   - `aeg-event-type: Notification`ヘッダーが必須
   - `dataVersion`は"1.0"を指定
   - `eventTime`はUTC形式で指定
   - `url`は実際のBlobストレージのURLに合わせて変更

3. デバッグ
   - Azure Functionsのログを確認
   - レスポンスのステータスコードと内容を確認

   Azure Speech Webhook テストの一連フロー
🔁 事前リセット（2回目以降の再テスト時）
① 古い .wav ファイルを削除する

※ .webm ファイルはそのままでOK（再利用可能）

② Event Grid Trigger を再発火

.webm → .wav 変換 → .wav アップロード → transcription job 作成までが実行される

🔄 コールバック環境の再構築
③ ngrok を再起動し、最新の HTTPS Forwarding URL を取得

④ local.settings.json の TRANSCRIPTION_CALLBACK_URL を更新

"TRANSCRIPTION_CALLBACK_URL": "https://<新しい-ngrok>.ngrok-free.app/api/transcription-callback"
⑤ PowerShell テストコマンドの -Uri も新しい ngrok URL に変更


Invoke-WebRequest -Uri "https://<新しい-ngrok>.ngrok-free.app/api/transcription-callback" ...
🧪 Webhook テスト準備
⑥ get_transcription_results_url.py を使って最新の transcription の resultsUrls.channel_0 を取得

⑦ sample-webhook.json を以下のように更新

self → 最新の job ID URL に

resultsUrls.channel_0 → 上記で取得した .json ダウンロードURLに差し替え

✅ テスト実行！
⑧ PowerShell の Invoke-WebRequest を実行して Webhook を模擬送信

powershell
Invoke-WebRequest -Uri "https://<新しい-ngrok>.ngrok-free.app/api/transcription-callback" `
                  -Method Post `
                  -Headers @{ "Content-Type" = "application/json" } `
                  -Body (Get-Content -Raw -Path "sample-webhook.json")
🔍 成功判定の目安
Azure Functions のログに TranscriptionCallback 成功ログが出る

.json 結果を正しく取得し、SQLへの書き込みまで完了

## テストエンドポイント

### TestProcessAudioについて
TestProcessAudioはローカル開発環境専用のテストエンドポイントです。

#### 目的と役割
- Event Grid Trigger（TriggerTranscriptionJob）のローカルテスト用代替手段
- 通常のフロー（Blob Storageへの.webmアップロード→Event Grid Trigger）をローカルで手動実行可能に
- .webm→.wav変換からtranscription job作成までの一連の処理をテスト可能

#### 使用方法
```powershell
# TestProcessAudioの実行
Invoke-RestMethod -Uri "http://localhost:7072/api/test/process-audio" -Method Post
```

#### 注意事項
- 本番環境では不要（ローカル開発環境専用）
- Event Gridがローカルで自動発火しない問題の回避策
- テスト目的でのみ使用すること

### データベース接続テスト
データベースの接続状態と基本的な操作を確認するためのテストエンドポイントを提供しています。

#### 1. データベース接続確認
```powershell
# データベース接続情報の確認
Invoke-RestMethod -Uri "http://localhost:7072/api/test/db-info" -Method Get

# データベース接続テスト
Invoke-RestMethod -Uri "http://localhost:7072/api/test/db-connection" -Method Get
```

#### 2. テストデータ挿入
Meetingsテーブルへのテストデータ挿入を確認するためのエンドポイントです。このエンドポイントは以下の目的で使用できます：

- データベースのINSERT操作が正常に機能するか確認
- ストアドプロシージャ（sp_ExtractSpeakersAndSegmentsFromTranscript）の動作確認
- トリガー（trg_AfterInsertMeeting）の動作確認
- 日本語文字化けの確認

```powershell
# テストデータの挿入
Invoke-RestMethod -Uri "http://localhost:7072/api/test/insert-meeting" -Method Get
```

レスポンス例：
```json
{
    "status": "success",
    "message": "テスト会議レコードの挿入に成功しました",
    "endpoint": "GET /api/test/insert-meeting",
    "timestamp": "2024-03-21 10:30:45"
}
```

注意事項：
- このエンドポイントは開発・テスト環境でのみ使用してください
- 本番環境では無効化することを推奨します
- テストデータは毎回新しいmeeting_idで挿入されます
- エラーが発生した場合は、詳細なエラーメッセージが返されます

① テストフローまとめ（Markdown形式）
markdown

# 音声認識・話者分離処理のローカルテストフロー

## STEP 1: `.wav` リセット（任意・再テスト時）
- 前回処理した `.wav` ファイルを削除（Blob Storage 上）
- `.webm` ファイルは再利用可

## STEP 2: Event Grid Trigger を手動発火（トランスクリプションジョブ作成）
1. PowerShell で以下を実行し、`eventgrid-test-payload.json` を生成・保存

```powershell
$event = @(
    @{
        id = [guid]::NewGuid().ToString()
        subject = "/blobServices/default/containers/moc-audio/blobs/meeting_71_user_27_2025-04-30T02-11-30-801.webm"
        eventType = "Microsoft.Storage.BlobCreated"
        eventTime = (Get-Date).ToUniversalTime().ToString("o")
        dataVersion = "1.0"
        data = @{
            api = "PutBlob"
            clientRequestId = [guid]::NewGuid().ToString()
            requestId = [guid]::NewGuid().ToString()
            eTag = "0x8DBB9715E8F04AF"
            contentType = "video/webm"
            contentLength = 123456
            blobType = "BlockBlob"
            url = "https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.webm"
            sequencer = "000000000000000000000000000000000000000000000000"
            storageDiagnostics = @{ batchId = [guid]::NewGuid().ToString() }
        }
    }
) | ConvertTo-Json -Depth 10

$event | Out-File -Encoding UTF8 -FilePath .\eventgrid-test-payload.json
Invoke-WebRequest で手動発火：

powershell

Invoke-WebRequest `
  -Uri "http://localhost:7072/runtime/webhooks/eventgrid?functionName=TriggerTranscriptionJob" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json"; "aeg-event-type" = "Notification" } `
  -Body (Get-Content -Raw -Path ".\eventgrid-test-payload.json")
STEP 3: Webhook テスト（transcription 結果を模擬POST）
ngrok http 7072 を実行して HTTPS Forwarding URL を取得

.env または local.settings.json の TRANSCRIPTION_CALLBACK_URL を更新

sample-webhook.json を編集（resultsUrls.channel_0 を最新URLに）

PowerShell で callback 送信：

powershell

Invoke-WebRequest `
  -Uri "https://<ngrok-url>.ngrok-free.app/api/transcription-callback" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body (Get-Content -Raw -Path "sample-webhook.json")
✅ テスト結果の確認
sql

SELECT * FROM dbo.ConversationSegments WHERE meeting_id = 71;
SELECT * FROM dbo.Speakers WHERE meeting_id = 71;
start_time, end_time, speaker_id, content が正しく登録されていれば成功

# 🔁 音声ファイル処理のローカルテスト構造

## 🎯 テスト目的
- .webm → .wav 変換
- Azure Speech への transcription job 登録
- transcription 結果（JSON）を受け取って SQL に書き込む
- 会話セグメントと話者情報を正確に登録できるか確認

---

## ✅ STEP 1: 前回の `.wav` を削除（必要なら）

- Storage に残っている `.wav` を削除
- `.webm` は再利用OK

---

## ✅ STEP 2: Event Grid Trigger を模擬発火

- `.webm` アップロードを見立てて、TriggerTranscriptionJob を PowerShell で起動

```powershell
Invoke-WebRequest `
  -Uri "http://localhost:7072/runtime/webhooks/eventgrid?functionName=TriggerTranscriptionJob" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json"; "aeg-event-type" = "Notification" } `
  -Body (Get-Content -Raw -Path "eventgrid-test-payload.json")

## 音声認識・話者分離処理のローカルテストフロー（更新版）

### 🎯 テスト目的
- `.webm` → `.wav` 変換
- Azure Speech への transcription job 登録
- transcription 結果（JSON）を受信
- 会話セグメント／話者情報を SQL に保存

---

### ✅ STEP 1: `.wav` を削除（再テスト時）
- ストレージ上の `.wav` を削除（`.webm` は残す）

---

### ✅ STEP 2: Event Grid Trigger を手動発火

```powershell
# eventgrid-test-payload.json 作成
$event = @(
    @{
        id = [guid]::NewGuid().ToString()
        subject = "/blobServices/default/containers/moc-audio/blobs/meeting_83_user_34_2025-05-19T07-20-38-755.webm"
        eventType = "Microsoft.Storage.BlobCreated"
        eventTime = (Get-Date).ToUniversalTime().ToString("o")
        dataVersion = "1.0"
        data = @{
            api = "PutBlob"
            clientRequestId = [guid]::NewGuid().ToString()
            requestId = [guid]::NewGuid().ToString()
            eTag = "0x8DBB9715E8F04AF"
            contentType = "video/webm"
            contentLength = 123456
            blobType = "BlockBlob"
            url = "https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_83_user_34_2025-05-19T07-20-38-755.webm"
            sequencer = "000000000000000000000000000000000000000000000000"
            storageDiagnostics = @{ batchId = [guid]::NewGuid().ToString() }
        }
    }
) | ConvertTo-Json -Depth 10

$event | Out-File -Encoding UTF8 -FilePath .\eventgrid-test-payload.json

# 発火
Invoke-WebRequest `
  -Uri "http://localhost:7072/runtime/webhooks/eventgrid?functionName=TriggerTranscriptionJob" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json"; "aeg-event-type" = "Notification" } `
  -Body (Get-Content -Raw -Path ".\eventgrid-test-payload.json")



## 🔐 Azure Entra ID 認証情報の取得・設定手順

本プロジェクトでは、Azure SQL Database に対して Entra ID（旧 Azure AD）を用いた認証を行います。以下の手順に従って `TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET` を取得し、`local.settings.json` に設定してください。

---

### ✅ 1. Azure Portal にログイン

Azure Portal（https://portal.azure.com）にアクセスし、対象の Azure サブスクリプションへログインします。

---

### ✅ 2. 認証情報の取得手順

#### 🆔 TENANT_ID の取得方法

1. 上部の検索バーで「**Microsoft Entra ID**」と検索して選択
2. 「概要」画面を開く
3. 表示されている「**テナント ID**」をコピー

#### 🆔 CLIENT_ID の取得方法

1. 上部の検索バーで「**アプリの登録（App registrations）**」と検索して選択
2. 対象アプリ（例：`AudioSalesAnalyser`）をクリック
3. 表示されている「**アプリケーション（クライアント）ID**」をコピー

#### 🔑 CLIENT_SECRET の取得方法

1. 上部の検索バーで「**アプリの登録（App registrations）**」と検索して選択
2. 対象アプリ（例：`AudioSalesAnalyser`）をクリック
3. 左メニューから「**管理** > **証明書とシークレット**」を選択
4. 「＋新しいクライアント シークレット」をクリック
5. 説明と有効期限を設定し、「追加」
6. 作成直後に表示される「**値（Value）**」をコピー  
   > ⚠ 一度離れると再表示できません。必ずこの場で控えてください

---

### 🧪 3. 認証情報の動作確認（任意）

以下の `curl` コマンドでトークンが取得できれば、認証情報は正しく機能しています。

```bash
curl -X POST https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token \
 -H "Content-Type: application/x-www-form-urlencoded" \
 -d "client_id=<CLIENT_ID>" \
 -d "client_secret=<CLIENT_SECRET>" \
 -d "scope=https://database.windows.net/.default" \
 -d "grant_type=client_credentials"
