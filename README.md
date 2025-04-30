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