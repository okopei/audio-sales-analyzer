# audio-sales-analyzer

## 必要要件
- Node.js v18以上
- Python 3.9以上
- Git

## 初回セットアップ手順

### 1. リポジトリのクローン
```bash
# リポジトリをクローン
git clone https://github.com/okopei/audio-sales-analyzer.git
cd audio-sales-analyzer
```

### 2. Next.jsアプリケーション（初回セットアップ）
```bash
# next-appディレクトリに移動
cd next-app

# Node.jsの依存パッケージをインストール
npm install

# 環境変数ファイルをコピー
cp .env.example .env.local

# 開発サーバー起動
npm run dev
```
→ http://localhost:3000 でアクセス可能

### 3. Python環境（初回セットアップ）
```bash
# python-apiディレクトリに移動
cd python-api

# 仮想環境作成
python -m venv venv

# 仮想環境の有効化
## Windows
venv\Scripts\activate
## macOS/Linux
source venv/bin/activate

# 必要なパッケージをインストール
pip install -r requirements.txt

# 環境変数ファイルをコピー
cp .env.example .env

# FastAPIサーバー起動
uvicorn main:app --reload
```
→ http://localhost:8000 でアクセス可能

## ローカル環境セットアップ（2回目以降）

### 1. Next.jsアプリケーション
```bash
# next-appディレクトリに移動
cd next-app

# 開発サーバー起動のみ
npm run dev
```
→ http://localhost:3000 でアクセス可能

### 2. Python環境
```bash
# python-apiディレクトリに移動
cd python-api

# 仮想環境の有効化のみ
## Windows
venv\Scripts\activate
## macOS/Linux
source venv/bin/activate

# FastAPIサーバー起動
uvicorn main:app --reload
```
→ http://localhost:8000 でアクセス可能

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

### 1. Gitブランチ命名規則

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

### 2. コミットメッセージ規則

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

### 3. コーディング規則

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

### 4. PRレビュールール

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

### Next.js関連

#### 1. `node_modules`に関するエラー
**発生状況：**
- パッケージの依存関係が壊れた場合
- `package.json`が更新された後の不整合
- Gitからクローンしたあとのモジュールエラー

**解決方法：**
```bash
# node_modulesを削除して再インストール
rm -rf node_modules
npm install
```

#### 2. ビルドエラー
**発生状況：**
- TypeScriptの型エラー
- キャッシュの不整合
- 環境変数の設定ミス

**解決方法：**
```bash
# Next.jsのキャッシュをクリア
npm run clean

# 必要に応じて再ビルド
npm run build
```

### Python関連

#### 1. パッケージの競合
**発生状況：**
- 異なるバージョンのパッケージが混在
- `requirements.txt`の更新後
- Python自体のバージョン不整合

**解決方法：**
```bash
# 仮想環境を再作成
rm -rf venv
python -m venv venv
source venv/bin/activate  # または venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. 環境変数エラー
**発生状況：**
- `.env`ファイルが存在しない
- 必要な環境変数が設定されていない
- 環境変数の値が不正

**解決方法：**
```bash
# .envファイルが存在することを確認
ls .env

# 必要に応じて.env.exampleからコピー
cp .env.example .env

# .envファイルの内容を確認
cat .env
```

#### 3. FastAPIサーバー起動エラー
**発生状況：**
- ポート8000が既に使用されている
- データベース接続エラー
- 依存パッケージの不足

**解決方法：**
```bash
# 使用中のポートを確認
## Windows
netstat -ano | findstr :8000
## macOS/Linux
lsof -i :8000

# 別のポートで起動
uvicorn main:app --reload --port 8001
```

### Git関連

- 誤って削除したファイルの復元
```bash
git checkout -- deleted-file
```

- コミット履歴の確認
```bash
# 詳細なログの確認
git log --oneline --graph

# 特定ファイルの変更履歴
git log -p filename
```

- ブランチの整理
```bash
# マージ済みブランチの削除
git branch --merged | grep -v "\*" | xargs -n 1 git branch -d
```
