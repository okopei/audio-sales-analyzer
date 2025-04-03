# AzureFunctions-Python-Feedback

フィードバック機能を提供するAzure Functions APIプロジェクトです。会話セグメントの取得、コメントの追加・参照、既読状態の管理などの機能を提供します。

## 機能

- 会話セグメント取得 API
- コメント取得 API
- 最新コメント取得 API
- コメント追加 API
- コメント既読状態更新 API

## 開発環境のセットアップ

### 前提条件

- Python 3.9以上
- Azure Functions Core Tools
- Azurite (Azureストレージエミュレーター)

### インストール手順

1. リポジトリのクローン
```
git clone <repository-url>
cd AzureFunctions-Python-Feedback
```

2. 仮想環境の作成と有効化
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
source .venv/bin/activate     # Linux/Mac
```

3. 依存パッケージのインストール
```
pip install -r requirements.txt
```

4. ローカル実行
```
func start
```

## API エンドポイント

### 会話セグメント取得 API
- エンドポイント: `GET /api/conversation/segments/{meeting_id}`
- 説明: 指定された会議IDに関連する会話セグメントを取得します

### コメント取得 API
- エンドポイント: `GET /api/comments/{segment_id}`
- 説明: 指定されたセグメントIDに関連するコメントを取得します

### 最新コメント取得 API
- エンドポイント: `GET /api/comments/latest?userId={user_id}&limit={limit}`
- 説明: ダッシュボード用の最新コメントを取得します
- クエリパラメータ:
  - `userId`: ユーザーID（省略時は1）
  - `limit`: 取得するコメント数（省略時は5）

### コメント追加 API
- エンドポイント: `POST /api/comments`
- 説明: 新しいコメントを追加します
- リクエストボディ:
  ```json
  {
    "segment_id": 123,
    "meeting_id": 456,
    "user_id": 789,
    "content": "コメント内容"
  }
  ```

### コメント既読状態更新 API
- エンドポイント: `POST /api/comments/read`
- 説明: コメントを既読としてマークします
- リクエストボディ:
  ```json
  {
    "comment_id": 123,
    "user_id": 789
  }
  ``` 