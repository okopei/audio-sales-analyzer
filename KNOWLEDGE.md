# 技術知識メモ

## データベース

### カラム制約

1. **PRIMARY KEY**
   - テーブルに1つだけ設定可能
   - NULLを許可しない
   - テーブルの主たる識別子として使用
   - インデックスが自動的に作成される
   - 例：`id UNIQUEIDENTIFIER PRIMARY KEY`

2. **UNIQUE**
   - テーブルに複数設定可能
   - NULLを許可する（設定による）
   - 重複を防ぐだけの制約
   - インデックスは作成されるが、主キーではない
   - 例：`email NVARCHAR(255) UNIQUE`

3. **REFERENCES（外部キー制約）**
   - 他のテーブルを参照する制約
   - データの整合性を保つ
   - 親テーブルに存在しない値は登録できない
   - 例：`user_id UNIQUEIDENTIFIER REFERENCES Users(id)`
   - `Users`テーブルの`id`カラムを参照する

### PRIMARY KEYとUNIQUEの使い分け
```sql
CREATE TABLE Users (
    id              UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),  -- テーブルの主キー（一意の識別子）
    email           NVARCHAR(255) UNIQUE,    -- 重複不可だが主キーではない
    ...
);
```

### REFERENCESの使用例
```sql
-- Usersテーブル（親テーブル）
CREATE TABLE Users (
    id   UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(255)
);

-- AudioRecordingsテーブル（子テーブル）
CREATE TABLE AudioRecordings (
    id      UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER REFERENCES Users(id),  -- Usersテーブルのidを参照
    title   NVARCHAR(255)
);

-- 以下のような操作が可能
INSERT INTO Users (id, name) VALUES (NEWID(), 'John');

-- 成功：存在するユーザーID
DECLARE @userId UNIQUEIDENTIFIER = (SELECT TOP 1 id FROM Users WHERE name = 'John');
INSERT INTO AudioRecordings (id, user_id, title) 
VALUES (NEWID(), @userId, 'Meeting');

-- エラー：存在しないユーザーID
INSERT INTO AudioRecordings (id, user_id, title)
VALUES (NEWID(), '999-not-exists', 'Test');  -- エラー！
```

使い分けの理由：
1. UNIQUEIDENTIFIERは人間が読みにくいが、システム的に扱いやすい
2. メールアドレスは変更される可能性があるため主キーには適さない
3. システムの内部処理（id）と外部向けの識別（email）を分離できる

### 実際の使用例
```sql
-- 以下のような登録は可能
INSERT INTO Users (email) VALUES ('user1@example.com');
INSERT INTO Users (email) VALUES ('user2@example.com');

-- 以下は既に同じメールアドレスが存在するためエラーになる
INSERT INTO Users (email) VALUES ('user1@example.com');  -- エラー！
```

### UNIQUEIDENTIFIER（SQL ServerのUUID）
- 128ビット（32文字）の一意な識別子
- 例：`123e4567-e89b-12d3-a456-426614174000`
- 特徴：
  1. グローバルで一意性が保証される
  2. 生成時に重複する可能性が極めて低い
  3. 分散システムでも安全に使える
  4. データベースのマージや移行が容易

#### UNIQUEIDENTIFIERを使用する理由
1. **分散システムでの利点**
   - サーバー間で同期なしにIDを生成可能
   - マイクロサービスアーキテクチャに適している

2. **セキュリティ**
   - 連番に比べて予測が困難
   - URLやAPIで使用しても安全

3. **スケーラビリティ**
   - シャーディング（データ分割）が容易
   - 将来的なシステム拡張に対応しやすい

#### デメリット
1. 可読性が低い
2. インデックスサイズが大きい
3. 文字列として扱う場合のストレージ消費

#### 使用例
```sql
CREATE TABLE Users (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),  -- 自動的にUNIQUEIDENTIFIERを生成
    email NVARCHAR(255)
);
```


## ベクトル検索の実装方法

### PostgreSQLでのベクトル保存（pgvector）
- PostgreSQLのpgvector拡張を使用
- OpenAIのテキスト埋め込みベクトル（1536次元）をデータベースに保存
- データベース内でベクトル類似性検索が可能
- `VECTOR`型を使用して実装

### Azure Cognitive Searchとの連携
- データベースのベクトルデータをAzure Cognitive Searchにインデックス同期
- より高度なベクトル検索（semantic search）が可能
- 用途に応じて検索方法を選択可能

### 使い分けのポイント
1. PostgreSQL（pgvector）
   - 直接的なベクトル検索
   - データベース内での高速な検索が必要な場合

2. Azure Cognitive Search
   - より高度な検索機能が必要な場合
   - 大規模なデータセットでの検索
   - フルテキスト検索との組み合わせ 

### ベクトル検索の仕組み

1. **ベクトルデータの生成と保存**
   - OpenAI Ada-2モデルでテキストをベクトル化
   - 1536次元のベクトルデータを生成
   - SQL Database: バックアップ用にJSON形式で保存
   - Azure Cognitive Search: `Collection(Edm.Single)`型で生のベクトルとして保存

2. **検索処理の流れ**
```
[検索クエリのテキスト]
    ↓
[OpenAI API] → ベクトル生成（1536次元）
    ↓
[Azure Cognitive Search] → 類似ベクトル検索
    ↓
[検索結果] → 類似度の高い文書を返却
```

3. **検索の特徴**
   - 意味的な類似性に基づく検索が可能
   - キーワードの完全一致に依存しない
   - 文脈を考慮した検索結果
   - HNSWアルゴリズムによる高速な類似度計算

4. **具体例**
   - 検索クエリ：「営業成績について」
   - 検索結果として以下のような類似の意味を持つテキストもヒット：
     - 「売上の状況」
     - 「セールスの実績」
     - 「販売のパフォーマンス」

5. **重要なポイント**
   - 全てのテキストは事前にベクトル化が必要
   - JSONはバックアップとしての役割
   - 実際の検索は数値ベクトル同士の類似度計算
   - 検索時にもベクトル生成のAPIコールが必要

## Azureのデータベースサービス

### メインのSQLサービス

1. **Azure SQL Database**
   - Azureのメインとなるリレーショナルデータベースサービス
   - Microsoft SQL Server（MS SQL）がベース
   - フルマネージドサービスとして提供
   - T-SQLを使用

2. **Azure SQL Managed Instance**
   - SQL Serverとほぼ100%の互換性を持つ
   - オンプレミスのSQL Serverからの移行に最適
   - より多くのSQL Server機能をサポート

3. **Azure SQL Server**
   - IaaS（Infrastructure as a Service）として提供
   - 仮想マシン上でSQL Serverを実行
   - 完全な管理権限が必要な場合に使用

### その他のマネージドデータベースサービス
- Azure Database for PostgreSQL
- Azure Database for MySQL
- Azure Database for MariaDB

※ AzureのネイティブなSQLはMicrosoft SQL Server（MS SQL）ベースとなっている 

## Azure Cognitive Searchのインデックス設計

### インデックスとは
- 検索サービスのためのデータ構造定義
- 検索機能、フィルタリング、ソートなどの機能を規定
- データの構造化と検索方法を定義

### 主な設定項目

1. **フィールド定義**
   - `searchable`: 検索対象とするか
   - `filterable`: フィルタリング可能にするか
   - `sortable`: ソート可能にするか
   - `key`: 主キーとして使用するか

2. **データ型**
   - `Edm.String`: テキストデータ
   - `Collection(Edm.Single)`: 数値配列（ベクトル用）
   - `Edm.DateTimeOffset`: 日時データ

3. **テキスト分析設定**
   - 言語固有の分析器指定（例：ja.microsoft）
   - 形態素解析による日本語対応
   - カスタム分析器の設定も可能

4. **ベクトル検索設定**
   - 次元数の指定
   - 検索アルゴリズムの選択（HNSW等）
   - 類似度計算方法の設定

### 検索機能の種類

1. **全文検索**
   - キーワードベースの検索
   - 形態素解析による精度向上
   - 日本語テキストの適切な処理

2. **ベクトル検索**
   - 意味的な類似性での検索
   - AIモデルによる文章の意味理解
   - 高速な近似最近傍探索

3. **ハイブリッド検索**
   - 全文検索とベクトル検索の組み合わせ
   - より正確な検索結果の提供
   - 柔軟な検索オプション

### 利点
- 高速な検索処理
- スケーラブルな検索機能
- 高度な日本語対応
- AIベースの意味検索
- 柔軟なカスタマイズ性 

## タグベースの評価システム

### 評価の二重構造
1. **音声データ直接の評価**
   - 個別の音声に対する評価
   - 具体的な事例としての評価
   - AudioRatingsテーブルで管理

2. **タグベースの評価**
   - カテゴリ単位での評価
   - ベストプラクティスの類型化
   - TagRatingsテーブルで管理

### 評価スコアの計算方法

1. **総合評価スコアの算出**
```
総合スコア = (音声評価 × 1.5) + (タグ評価の平均 × 2.0)
```

2. **タグ評価の集計**
- 一つの音声に複数のタグが付いている場合
- それぞれのタグの評価スコアを平均化
- より高評価のタグを持つ音声が優先的に表示

### 使用例

1. **タグの評価付け**
```sql
-- 「セールストーク」タグに高評価を付ける
INSERT INTO TagRatings (
    tag_id,    -- 「セールストーク」タグのID
    rating,    -- 評価スコア（例：4.8）
    rated_by,  -- 評価者のユーザーID
    comment    -- 「効果的な説明方法として推奨」
)
```

2. **検索への影響**
- 検索クエリ：「商品説明」
- 結果の優先順位：
  1. 高評価の音声 + 高評価のタグ
  2. 高評価の音声のみ
  3. 高評価のタグのみ
  4. その他の音声

### 活用メリット

1. **きめ細かい評価システム**
   - 個別事例の評価
   - カテゴリ単位での評価
   - 複数の視点からの品質評価

2. **効果的なナレッジ管理**
   - ベストプラクティスの体系化
   - 優良事例の類型化
   - 組織的な品質向上

3. **柔軟な検索機能**
   - 多角的な評価基準
   - 状況に応じた検索結果
   - 学習教材としての活用

4. **運用上の利点**
   - 評価基準の段階的な改善
   - 新人教育への活用
   - 営業品質の可視化

### 実装時の注意点

1. **パフォーマンス考慮**
   - タグ評価の集計処理の最適化
   - インデックス更新のタイミング制御
   - キャッシュ戦略の検討

2. **評価基準の設計**
   - 評価スコアの重み付けバランス
   - タグ付けガイドラインの整備
   - 評価者トレーニングの実施

3. **システムの拡張性**
   - 新しい評価軸の追加
   - 評価アルゴリズムの調整
   - レポーティング機能の拡充 

## Gitでの機密情報管理

### 機密情報の誤コミット問題

#### 問題の概要
- **関連システム**: Git、GitHub
- **問題**: 機密情報（APIキー、接続文字列など）が誤ってGitリポジトリにコミットされた
- **発生状況**: `local.settings.json`や`.env.local`などの設定ファイルをコミットした場合
- **影響**: セキュリティリスク、GitHubのシークレットスキャンによるプッシュブロック

#### 解決方法

1. **ファイルをGitの追跡から除外**
   ```bash
   git rm --cached <ファイルパス>
   ```
   例：
   ```bash
   git rm --cached AzureFunctions-Python-api/local.settings.json
   git rm --cached next-app/.env.local
   ```

2. **.gitignoreの確認と更新**
   以下のパターンが`.gitignore`に含まれていることを確認：
   ```
   # 機密情報を含むファイル
   local.settings.json
   .env.local
   .env.development.local
   .env.test.local
   .env.production.local
   ```

3. **テンプレートファイルの作成**
   機密情報を含まないテンプレートファイルを作成：
   ```bash
   # 例：local.settings.template.jsonの作成
   cp local.settings.json local.settings.template.json
   # テンプレートファイル内の機密情報をプレースホルダーに置き換え
   ```

4. **変更をコミット**
   ```bash
   git add .gitignore
   git add *template*
   git commit -m "chore: gitignoreの更新とテンプレートファイルの追加"
   ```

5. **APIキーのローテーション**
   誤ってコミットされた機密情報（APIキーなど）は再発行する

#### 履歴からの完全削除（必要な場合）
注意: 共有リポジトリの場合は他の開発者と調整が必要

```bash
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch <ファイルパス>" --prune-empty --tag-name-filter cat -- --all
git push origin --force --all
```

#### 予防策
1. **pre-commitフックの導入**
   - [git-secrets](https://github.com/awslabs/git-secrets)などのツールを使用
   - コミット前に機密情報をスキャンして防止

2. **環境変数の適切な管理**
   - 開発環境: `.env.local`や`local.settings.json`を使用（Gitにコミットしない）
   - 本番環境: Azure Key VaultやGitHub Secretsなどのシークレット管理サービスを使用

3. **テンプレートファイルの活用**
   - `.env.template`や`local.settings.template.json`を用意
   - 必要な変数名のみを記載し、実際の値は記載しない

4. **ドキュメント化**
   - READMEに環境変数の設定手順を記載
   - 新しい開発者のオンボーディングを容易にする 

# フィードバック機能の実装

## アーキテクチャ設計

### 1. バックエンド機能の分離

フィードバック機能は独立したAzure Functionsプロジェクトとして実装。これにより以下の利点を得られる：

- 責任の分離 - 文字起こし処理と独立した開発・デプロイが可能
- 適切なスケーリング - フィードバック機能はリアルタイム性が高く軽量な処理が中心
- リソース競合の防止 - 重い処理（文字起こし）と分離することでパフォーマンス向上

### 2. SQL接続方式

Azure Functions SQLバインディングを活用し、pyodbcを使わずに実装：

```python
@app.function_name(name="GetConversationSegments")
@app.route(route="api/conversation/segments/{meeting_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="segmentsQuery", 
    type="sql", 
    CommandText="SELECT s.segment_id, s.user_id, s.speaker_id, s.meeting_id, s.content, s.file_name, s.file_path, s.file_size, s.duration_seconds, s.status, s.inserted_datetime, s.updated_datetime, sp.speaker_name, sp.speaker_role FROM dbo.ConversationSegments s LEFT JOIN dbo.Speakers sp ON s.speaker_id = sp.speaker_id WHERE s.deleted_datetime IS NULL", 
    ConnectionStringSetting="SqlConnectionString"
)
```

local.settings.json:
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
    "SqlConnectionString": "Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=AudioSalesAnalyzer;Trusted_Connection=yes;"
  },
  "Host": {
    "LocalHttpPort": 7073,
    "CORS": "http://localhost:3000",
    "CORSCredentials": true
  }
}
```

### 3. API設計

| エンドポイント | メソッド | 説明 |
|--------------|-------|------|
| `/api/conversation/segments/{meeting_id}` | GET | 会話セグメント取得 |
| `/api/comments/{segment_id}` | GET | コメント取得 |
| `/api/comments` | POST | コメント追加 |
| `/api/comments/read` | POST | コメント既読状態更新 |

## データモデル

### 関連テーブル

- `ConversationSegments` - 会話内容、話者情報を保持
- `Comments` - コメント情報を保持
- `CommentReads` - コメントの既読状態を管理
- `Speakers` - 話者情報を管理

### TypeScriptでのインターフェース

```typescript
interface ConversationSegment {
  segment_id: number
  user_id: number
  speaker_id: number
  meeting_id: number
  content: string
  file_name: string
  file_path: string
  file_size: number
  duration_seconds: number
  status: string
  inserted_datetime: string
  updated_datetime: string
  speaker_name?: string
  speaker_role?: string
}

interface Comment {
  comment_id: number
  segment_id: number
  meeting_id: number
  user_id: number
  user_name: string
  content: string
  inserted_datetime: string
  updated_datetime: string
  readers: CommentReader[]
}

interface CommentReader {
  reader_id: number
  read_datetime: string
}
```

## フロントエンド実装

### ディレクトリ構造

```
next-app/
├── src/
│   ├── app/
│   │   ├── feedback/
│   │   │   ├── [meeting_id]/
│   │   │   │   └── page.tsx   # 詳細ページ
│   │   │   └── page.tsx       # 一覧ページ
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   └── feedback.ts    # API通信モジュール
```

### API通信モジュール

API呼び出しの統一インターフェースを実装：

```typescript
export const getConversationSegments = async (meetingId: string | number) => {
  try {
    const response = await fetch(`http://localhost:7073/api/conversation/segments/${meetingId}`)
    const data = await response.json()
    if (!data.success) {
      throw new Error(data.message || 'セグメント取得に失敗しました')
    }
    return data.segments
  } catch (error) {
    console.error('会話セグメント取得エラー:', error)
    throw error
  }
}
```

### UI実装

- チャットのような表示形式を採用
- 話者によって背景色を変更 (営業担当：青系、顧客：緑系)
- コメント表示と追加機能を実装
- 既読状態の自動管理機能を実装

## デプロイ方法

1. Azure Functionプロジェクトのデプロイ
   ```
   cd AzureFunctions-Python-Feedback
   func azure functionapp publish <function-app-name>
   ```

2. Next.jsアプリケーションのデプロイ
   ```
   cd next-app
   pnpm build
   # Vercelなどへのデプロイ手順
   ```

## 今後の拡張可能性

1. **リアルタイム通知機能**
   - WebSocketやSignalRを活用した即時通知機能

2. **AI分析機能**
   - 会話内容の自動タグ付け
   - 感情分析によるハイライト表示

3. **オーディオ連携機能**
   - コメント時点のオーディオタイムスタンプリンク
   - 音声再生機能と連動したUI

4. **レポート機能**
   - コメントや会話内容を基にした自動レポート生成

## 開発時の注意点

1. **CORS設定**
   - フロントエンドとバックエンドの接続時にCORS問題が発生しやすい
   - local.settings.jsonの設定を適切に行う必要がある

2. **TypeScript型安全性**
   - APIレスポンスとフロントエンドの型定義を一致させる

3. **SQL接続**
   - Azure FunctionsのSQL接続はバインディングを活用するとシンプルに実装可能
   - パフォーマンスのためにクエリの最適化が必要な場合もある

# 音声部分再生の要件

## 必要な情報
1. **音声ファイルのURL**
2. **開始時間**（秒単位）
3. **終了時間**（秒単位）

## 実装方法
```typescript
const AudioPlayer = ({ audioUrl, startTime, endTime }: {
  audioUrl: string
  startTime: number  // 秒単位
  endTime: number    // 秒単位
}) => {
  const audioRef = useRef<HTMLAudioElement>(null)

  const playSegment = () => {
    if (!audioRef.current) return
    audioRef.current.currentTime = startTime
    audioRef.current.play()

    const stopAtEnd = () => {
      if (audioRef.current?.currentTime >= endTime) {
        audioRef.current.pause()
      }
    }

    audioRef.current.addEventListener('timeupdate', stopAtEnd)
  }

  return <audio ref={audioRef} src={audioUrl} />
}
```

## 技術的なポイント
- HTML5のaudio要素の`currentTime`プロパティを使用
- `timeupdate`イベントで終了時間を監視
- 指定された時間範囲のみを再生可能

## データベース設計への影響
フィードバック画面で音声再生を実装するために、以下のデータが必要：
- 音声ファイルの保存場所（URL）
- 各セグメントの開始時間
- 各セグメントの終了時間

# Azure StorageのURL構築に関する問題

## 問題
- Azure Blob StorageのURL構築時に403エラーが発生
- URLの形式が正しくない（SASトークンとファイル名の間に?が不足）
- 環境変数の重複と混乱
- SASトークンの権限が過剰（racwdlmeo）
- SASトークンの認証エラー（署名が正しくない）

## 解決策
1. 環境変数の整理
   - 重複した環境変数を削除
   - 必要な環境変数のみを保持
   - コメントを追加して整理

2. URL構築ロジックの修正
   - SASトークンとファイル名の間に?を追加
   - デバッグログの追加
   - エラーハンドリングの改善

3. SASトークンの権限見直し
   - 読み取り（Read）とリスト（List）のみに制限
   - 新しいSASトークンを生成
   - 環境変数を更新

4. SASトークンの再生成
   - Azure Portalで新しいSASトークンを生成
   - 適切な権限設定
   - 正しい署名方法の選択

## 環境変数の設定
```env
NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME=audiosalesanalyzeraudio
NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME=moc-audio
NEXT_PUBLIC_AZURE_STORAGE_SAS_TOKEN=sp=rl&st=2025-04-15T06:57:11Z&se=2026-04-01T14:57:11Z&spr=https&sv=2024-11-04&sr=c&sig=h4KOq0I%2FbZc4kA%2B6ZBCKCw5Ei4%2FfAr302lbiUOP0Ldg%3D
```

## 注意点
- SASトークンとファイル名の間に?が必要
- 環境変数は`NEXT_PUBLIC_`プレフィックスを使用してクライアントサイドで利用可能にする
- デバッグログを活用してURLの構築を確認する
- SASトークンの権限は必要最小限に制限する
- SASトークンの署名方法を確認する

## 正しいURLの形式
```
https://{ストレージアカウント名}.blob.core.windows.net/{ファイル名}?{SASトークン}
```

例：
```
https://audiosalesanalyzeraudio.blob.core.windows.net/1742097766757_meeting_001.wav?sp=rl&st=2025-04-15T06:57:11Z&se=2026-04-01T14:57:11Z&spr=https&sv=2024-11-04&sr=c&sig=h4KOq0I%2FbZc4kA%2B6ZBCKCw5Ei4%2FfAr302lbiUOP0Ldg%3D
```

## SASトークンの権限
- `sp=rl`：より広範な権限を含む
- 前回の`sp=racwdlmeo`より多くの権限
- 必要な権限を適切に設定

## SASトークンの生成手順
1. Azure Portalにログイン
2. ストレージアカウントを選択
3. 左メニューから「Shared Access Signature」を選択
4. 以下の設定で新しいSASトークンを生成：
   - 許可されたサービス：Blob
   - 許可されたリソースタイプ：コンテナー、オブジェクト
   - 許可されたアクセス許可：読み取り、リスト、追加、作成、削除、更新
   - 開始時間：現在時刻
   - 有効期限：適切な期間（例：1年）
   - 許可されたプロトコル：HTTPSのみ
   - 署名方法：アカウントキー

# SASトークンの署名エラー詳細

## 1. ストレージアカウントキーの不一致
### 問題点
- Azure PortalでSASトークンを生成する際に使用したストレージアカウントキーが、現在のストレージアカウントのキーと異なる
- キーのローテーション（更新）が行われた可能性がある

### 影響
- 署名の検証に失敗
- 403エラーが発生
- アクセスが拒否される

### 確認方法
1. Azure Portalで現在のストレージアカウントキーを確認
2. SASトークン生成時に使用したキーと比較
3. キーのローテーション履歴を確認

## 2. パラメータの順序の不一致
### 問題点
- SASトークンのパラメータの順序がAzureの期待する形式と異なる
- 署名生成時のパラメータ順序と検証時の順序が一致していない

### 正しい順序
```typescript
const stringToSign = [
  permissions,    // sp
  startTime,      // st
  expiryTime,     // se
  canonicalizedResource,  // リソースパス
  identifier,     // si
  ipRange,        // sip
  protocol,       // spr
  version,        // sv
  resourceTypes,  // sr
  cacheControl,   // rscc
  contentDisposition,  // rscd
  contentEncoding,     // rsce
  contentLanguage,     // rscl
  contentType          // rsct
].join('\n')
```

### 影響
- 署名の検証に失敗
- 403エラーが発生
- アクセスが拒否される

## 3. エンコード/デコードの問題
### 問題点
- URLエンコード/デコードの処理が不適切
- 特殊文字（例：`%`、`&`、`=`）のエンコードが正しく行われていない
- Base64エンコードの処理に問題がある

### 影響
- 署名の検証に失敗
- 403エラーが発生
- アクセスが拒否される

### 確認すべき点
1. **URLエンコード**：
   - `%` → `%25`
   - `&` → `%26`
   - `=` → `%3D`

2. **Base64エンコード**：
   - 正しいエンコード方式を使用
   - パディングの処理が適切

3. **特殊文字の処理**：
   - 署名に含まれる特殊文字の適切なエンコード
   - デコード時の文字化け防止

## トラブルシューティング手順
1. **ストレージアカウントキーの確認**：
   - Azure Portalで現在のキーを確認
   - 必要に応じてキーを再生成
   - 新しいキーでSASトークンを生成

2. **パラメータ順序の確認**：
   - Azureのドキュメントで正しい順序を確認
   - パラメータの順序を修正
   - 新しいSASトークンを生成

3. **エンコード/デコードの確認**：
   - URLエンコードの処理を確認
   - Base64エンコードの処理を確認
   - 特殊文字の適切な処理を確認

## 推奨される対応
1. Azure Portalで新しいSASトークンを生成
2. 環境変数を更新
3. アプリケーションを再起動
4. ブラウザのキャッシュをクリア
5. デバッグログでURL構築を確認

# Azure Storageアカウントのトラブルシューティング

## 403エラーの原因と解決策

### 1. ストレージアカウントの状態確認
```typescript
// 確認すべき項目
{
  subscription: {
    status: 'Active' | 'Disabled' | 'Deleted',
    paymentStatus: 'Current' | 'PastDue'
  },
  storageAccount: {
    status: 'Online' | 'Offline',
    provisioningState: 'Succeeded' | 'Failed',
    networkRules: {
      defaultAction: 'Allow' | 'Deny',
      ipRules: string[],
      virtualNetworkRules: string[]
    }
  }
}
```

### 2. アクセス制限の確認
1. **ネットワーク設定**:
   - パブリックアクセスが許可されているか
   - IPアドレスが許可されているか
   - 仮想ネットワークの設定

2. **ファイアウォール設定**:
   - 必要なIPアドレスの許可
   - 仮想ネットワークの設定
   - サービスエンドポイントの設定

### 3. 認証情報の確認
1. **ストレージアカウントキー**:
   - キーが有効か
   - キーのローテーション履歴
   - アクセス許可の設定

2. **SASトークン**:
   - 権限設定の確認
   - 時間範囲の確認
   - 署名の検証

### 4. トラブルシューティング手順
1. **Azure Portalでの確認**:
   - サブスクリプションの状態
   - ストレージアカウントの状態
   - ネットワーク設定
   - アクセスキー

2. **SASトークンの再生成**:
   - 新しいSASトークンを生成
   - 適切な権限設定
   - 正しい時間範囲

3. **ネットワーク設定の確認**:
   - パブリックアクセスの許可
   - IPアドレスの許可
   - ファイアウォール設定

### 5. エラーメッセージの解釈
```typescript
// 403エラーの詳細
{
  errorCode: 'AuthenticationFailed',
  message: 'Server failed to authenticate the request',
  possibleCauses: [
    'Invalid storage account key',
    'Invalid SAS token signature',
    'Expired SAS token',
    'Insufficient permissions',
    'Network restrictions'
  ]
}
```

### 6. ベストプラクティス
1. **定期的な確認**:
   - サブスクリプションの状態
   - ストレージアカウントの状態
   - ネットワーク設定

2. **セキュリティ設定**:
   - 最小限の権限設定
   - 適切なネットワーク制限
   - 定期的なキーのローテーション

3. **モニタリング**:
   - アクセスログの確認
   - エラーアラートの設定
   - パフォーマンスモニタリング

# Azure Storageのトラブルシューティング表

## 問題点、対応方法、検証結果の管理

| 問題点 | 対応方法 | 検証結果 | ステータス | 備考 |
|--------|----------|----------|------------|------|
| **サブスクリプションの状態** | 1. Azure Portalでサブスクリプションの状態を確認<br>2. 支払い状況を確認<br>3. リソースグループの状態を確認 | ✅ アクティブ<br>✅ 支払い状況：正常<br>✅ リソースグループ：存在 | 完了 | サブスクリプションは正常に動作中 |
| **ストレージアカウントの状態** | 1. Azure Portalでストレージアカウントの状態を確認<br>2. プロビジョニング状態を確認<br>3. アクティビティログを確認 | ✅ プロビジョニング状態：Succeeded<br>✅ ディスク状態：Available<br>✅ 作成日：2025/2/8 10:27:12 | 完了 | ストレージアカウントは正常に動作中 |
| **ネットワーク設定** | 1. パブリックアクセスの設定を確認<br>2. ファイアウォールルールを確認<br>3. 仮想ネットワークの設定を確認 | ✅ アクセス許可：All networks<br>✅ セキュア転送：Enabled<br>✅ TLSバージョン：1.2 | 完了 | ネットワーク設定は適切 |
| **ストレージアカウントキー** | 1. 現在のキーを確認<br>2. キーのローテーション履歴を確認<br>3. 新しいキーを生成 | ✅ キー1：有効（最終更新：2025/2/8）<br>✅ キー2：有効（最終更新：2025/2/8）<br>⚠️ 66日間更新なし | 要確認 | キーは有効だが、更新が必要な可能性あり |
| **コンテナーの設定** | 1. コンテナーの存在確認<br>2. アクセスレベル確認<br>3. パブリックアクセス設定確認 | ✅ コンテナー：存在<br>✅ リース状態：Available<br>✅ 暗号化：account-encryption-key | 完了 | コンテナーは正常に設定されている |
| **SASトークンの設定** | 1. 権限設定を確認（sp=rl）<br>2. 時間範囲を確認<br>3. プロトコル設定を確認<br>4. リソースタイプを確認 | ✅ 権限：Read, List（sp=rl）<br>✅ 開始：2025/4/15 15:57:11<br>✅ 終了：2026/4/1 23:57:11<br>✅ プロトコル：HTTPS<br>✅ リソース：Container | 完了 | 適切な権限と設定で生成済み |
| **URL構築の問題** | 1. URLの形式を確認<br>2. SASトークンの配置を確認<br>3. エンコード処理を確認 | ✅ ベースURL：正しい<br>✅ SASトークン：正しい形式<br>✅ エンコード：適切 | 完了 | Blob SAS URLが正しく生成されている |
| **エンコード/デコード** | 1. URLエンコードの処理を確認<br>2. Base64エンコードの処理を確認<br>3. 特殊文字の処理を確認 | ✅ URLエンコード：適切<br>✅ 特殊文字：正しく処理<br>✅ 署名：正しく生成 | 完了 | エンコーディングは適切 |
| **クライアント側の実装** | 1. コードのURL構築ロジックを確認<br>2. エラーハンドリングを確認<br>3. デバッグログを確認 | 未検証 | 未対応 | クライアント側の実装を確認する必要あり |

## 確認済みの設定

### SASトークン設定
```typescript
{
  sasToken: {
    permissions: 'rl',  // Read, List
    startTime: '2025-04-15T06:57:11Z',
    expiryTime: '2026-04-01T14:57:11Z',
    protocol: 'https',
    version: '2024-11-04',
    resourceType: 'c',  // Container
    signature: 'h4KOq0I/bZc4kA+6ZBCKCw5Ei4/fAr302lbiUOP0Ldg='
  }
}
```

### Blob SAS URL
```typescript
{
  baseUrl: 'https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio',
  sasToken: 'sp=rl&st=2025-04-15T06:57:11Z&se=2026-04-01T14:57:11Z&spr=https&sv=2024-11-04&sr=c&sig=h4KOq0I%2FbZc4kA%2B6ZBCKCw5Ei4%2FfAr302lbiUOP0Ldg%3D',
  fullUrl: 'https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio?sp=rl&st=2025-04-15T06:57:11Z&se=2026-04-01T14:57:11Z&spr=https&sv=2024-11-04&sr=c&sig=h4KOq0I%2FbZc4kA%2B6ZBCKCw5Ei4%2FfAr302lbiUOP0Ldg%3D'
}
```

## 次のステップ

1. **環境変数の更新**
   ```env
   NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME=audiosalesanalyzeraudio
   NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME=moc-audio
   NEXT_PUBLIC_AZURE_STORAGE_SAS_TOKEN=sp=rl&st=2025-04-15T06:57:11Z&se=2026-04-01T14:57:11Z&spr=https&sv=2024-11-04&sr=c&sig=h4KOq0I%2FbZc4kA%2B6ZBCKCw5Ei4%2FfAr302lbiUOP0Ldg%3D
   ```

2. **クライアント側の実装確認**
   - コードのURL構築ロジックを確認
   - エラーハンドリングを確認
   - デバッグログを確認

3. **動作確認**
   - アプリケーションを再起動
   - ブラウザのキャッシュをクリア
   - 音声ファイルのアクセスを確認

# SASトークンの更新履歴

## 2024-04-15の更新
- **更新日時**: 2024-04-15
- **有効期間**: 2025-04-15 06:57:11 UTC から 2026-04-01 14:57:11 UTC
- **権限**: Read, List (sp=rl)
- **プロトコル**: HTTPS のみ
- **リソースタイプ**: Container (sr=c)
- **バージョン**: 2024-11-04

### 設定内容
```typescript
interface SASTokenSettings {
  permissions: 'rl' // Read, List のみ
  startTime: '2025-04-15T06:57:11Z'
  expiryTime: '2026-04-01T14:57:11Z'
  protocol: 'https'
  version: '2024-11-04'
  resourceType: 'c' // Container
  signature: 'h4KOq0I/bZc4kA+6ZBCKCw5Ei4/fAr302lbiUOP0Ldg='
}
```

### 環境変数設定
```typescript
NEXT_PUBLIC_AZURE_STORAGE_ACCOUNT_NAME=audiosalesanalyzeraudio
NEXT_PUBLIC_AZURE_STORAGE_CONTAINER_NAME=moc-audio
NEXT_PUBLIC_AZURE_STORAGE_SAS_TOKEN=sp=rl&st=2025-04-15T06:57:11Z&se=2026-04-01T14:57:11Z&spr=https&sv=2024-11-04&sr=c&sig=h4KOq0I%2FbZc4kA%2B6ZBCKCw5Ei4%2FfAr302lbiUOP0Ldg%3D
```

### 重要な注意点
1. アプリケーションの再起動が必要
2. ブラウザキャッシュのクリア推奨
3. デバッグログでURL構築を確認
4. 音声ファイルの再生テスト実施

### トラブルシューティング
- 403エラーが発生した場合：
  - SASトークンの有効期限確認
  - 権限設定の確認（Read, List）
  - プロトコル（HTTPS）の確認
  - 署名の正当性確認

- 404エラーが発生した場合：
  - コンテナ名の確認
  - ファイルパスの正規化確認
  - ストレージアカウント名の確認

# 音声再生の問題解決進展

## SASトークンの問題解決 (2024-04-15)
### 解決した問題
- 403エラー（認証エラー）が発生
- URLにコンテナ名が含まれていなかった

### 解決方法
1. URLの構築ロジックを修正
   ```typescript
   const baseUrl = `https://${storageAccount}.blob.core.windows.net/`
   const containerPath = `${container}/${normalizedPath}`
   const encodedPath = encodeURIComponent(containerPath)
   ```
2. コンテナ名を環境変数から取得するように変更
3. パスの正規化処理を改善

### 効果
- 403エラーが解消
- 新しい問題（currentTimeの設定エラー）が顕在化

## 新しい問題：currentTimeの設定エラー
### エラー内容
```
TypeError: Failed to set the 'currentTime' property on 'HTMLMediaElement': The provided double value is non-finite.
at handlePlay (AudioSegmentPlayer.tsx:109:35)
```

### 考えられる原因
1. `startTime`プロパティが不正な値（NaN、Infinity、undefined）
2. 音声ファイルのメタデータが正しく読み込まれていない
3. `audioRef.current`の状態が不安定

### 次のステップ
1. `startTime`の値をログ出力して確認
2. `onLoadedMetadata`イベントの後にcurrentTimeを設定するように修正
3. 音声ファイルの読み込み状態を確認してからcurrentTimeを設定

## 音声再生機能の修正（2024-04-15）

### ブランチ名
`feature/audio-player-implementation`

### 変更内容の概要
- 音声ファイルの再生機能を実装
- Azure Blob Storageからの音声ファイル取得を実装
- 音声再生のUI/UXを実装

### 詳細な説明
1. 音声ファイルの再生機能
   - HTML5 Audio APIを使用した再生機能
   - 開始時間・終了時間の指定による部分再生
   - 再生状態の管理（再生/停止/一時停止）

2. Azure Blob Storage連携
   - SASトークンを使用した安全なアクセス
   - 音声ファイルのURL構築ロジック
   - エラーハンドリングの実装

3. UI/UX実装
   - 再生コントロール（再生/停止ボタン）
   - 再生時間の表示
   - エラー表示の実装

### 確認事項
- [x] 音声ファイルの再生が正常に動作
- [x] 部分再生（開始時間・終了時間指定）が機能
- [x] エラーハンドリングが適切に動作

### 次回の作業予定
1. 音声再生の品質改善
   - バッファリング処理の最適化
   - 再生の安定性向上

2. UI/UXの改善
   - プログレスバーの実装
   - 音量コントロールの追加
   - 再生速度調整機能の追加

3. エラー処理の強化
   - より詳細なエラーメッセージ
   - リトライ機能の実装
   - フォールバック処理の追加

### 注意事項
- 環境変数の設定が正しいことを確認
- 音声ファイルのパスが正しく設定されていることを確認
- ブラウザの互換性を考慮した実装

## FunctionAppの要件と責務

### AzureFunctions-Python-api
#### 主な機能
- 音声録音とBLOBストレージへの保存
- 認証・認可機能
- 会議基本情報の管理
- コメント機能
- 会話セグメントの管理

#### 技術要件
- HTTPトリガーによるAPIエンドポイント
- BLOBストレージへのファイル保存
- SQLデータベースとの連携
- CORS対応
- エラーハンドリング

### AzureFunctions-Python-SpeakerDiarization
#### 主な機能
- 音声ファイルの処理（Azure Speech Services）
- 話者分離機能
- 文字起こし処理
- 処理結果のデータベース保存

#### 技術要件
- EventGrid/BlobTriggerによるイベント処理
- Azure Speech Servicesとの連携
- 重い処理のための適切なスケーリング
- エラーハンドリングとリトライ機能

### 各FunctionAppの連携フロー
1. 音声録音・保存フロー
   ```
   フロントエンド → AzureFunctions-Python-api → BLOBストレージ
   ```

2. 音声処理フロー
   ```
   BLOBストレージ → AzureFunctions-Python-SpeakerDiarization → データベース
   ```

### 注意点
- 各FunctionAppは独立したスケーリングが可能
- 開発環境と本番環境で適切な設定が必要
- エラーハンドリングとログ管理が重要
- セキュリティ対策（認証・認可）の実装が必要

### 音声処理のトリガー機構
#### 監視対象
- `moc-audio`コンテナ内の音声ファイル

#### トリガー方法
1. **EventGridTrigger**
   - 新規ファイルアップロードを検知
   - イベントベースの処理開始
   - スケーラブルな処理が可能

2. **BlobTrigger**
   - `moc-audio`コンテナの変更を直接監視
   - ファイル追加時に自動処理
   - ローカル開発環境でも動作

#### 処理フロー
```
BLOBストレージ（moc-audio） → トリガー検知 → 音声処理 → データベース保存
```

#### 注意点
- 両方のトリガーが同時に動作する可能性があるため、冪等性を考慮
- 処理中のファイルの重複処理を防ぐ仕組みが必要
- エラー発生時のリトライ処理の実装が必要

## トラブルシューティング

### APIエラー

#### 1. `/api/members-meetings` 500エラー

**問題**: `GET http://localhost:7071/api/members-meetings?account_status=ACTIVE` で500エラーが発生

**発生状況**:
- フロントエンドから`/api/members-meetings`エンドポイントに`account_status=ACTIVE`パラメータを付けてリクエスト
- Azure Functionsの`get_members_meetings`関数で処理中にエラーが発生

**原因**:
1. `Users`テーブルから`account_status`カラムを取得していなかった
2. `Meetings`テーブルとの結合で`account_status`を取得していなかった
3. エラーハンドリングが不十分だった

**解決方法**:
1. `Users`テーブルのクエリに`account_status`カラムを追加
2. `Meetings`テーブルとの結合クエリに`account_status`を追加
3. エラーハンドリングを改善し、詳細なログを記録するように修正

**関連システム**:
- Azure Functions (Python)
- SQL Database
- Next.jsフロントエンド

# 音声ファイル形式の比較

## WAV形式
- **特徴**
  - 非圧縮形式
  - 高品質な音声データを保持
  - ファイルサイズが大きい
  - ヘッダー: `52 49 46 46` (RIFF)
- **用途**
  - 音声認識に最適
  - 高品質な音声録音
  - 編集・加工が必要な場合
- **メリット**
  - 音声認識の精度が高い
  - 編集が容易
  - 互換性が高い
- **デメリット**
  - ファイルサイズが大きい
  - ストレージ容量を多く使用
  - 転送に時間がかかる

## WebM形式
- **特徴**
  - 圧縮形式
  - ファイルサイズが小さい
  - ヘッダー: `1A 45 DF A3`
- **用途**
  - ブラウザでの録音
  - ストリーミング
  - モバイルアプリでの録音
- **メリット**
  - ファイルサイズが小さい
  - 転送が速い
  - ストレージ容量を節約
- **デメリット**
  - 音声認識の精度が低下する可能性
  - 編集が難しい
  - 変換が必要な場合がある

## 本システムでの使用
  - 必要に応じてWAVに変換

## 変換処理
- WebMからWAVへの変換が必要な場合
  - ffmpegを使用
  - 16-bit PCM
  - 16kHzサンプリングレート
  - モノラル音声

## 注意点
1. ファイル形式の確認は重要
2. 変換処理はリソースを消費
3. 適切な形式選択が重要
4. エラーハンドリングが必要

## トラブルシューティング一覧表

| エラーNo | システム | 問題 | 発生状況 | 解決方法 | 結果 | 次のステップ |
|---------|---------|------|----------|----------|------|------------|
| E001 | Azure Speech SDK | 話者分離の設定エラー | `PropertyId`クラスに`SpeechServiceConnection_EnableDiarization`属性が存在しない | `set_property`メソッドに文字列としてプロパティ名を渡すように修正 | エラー：`property_id value must be PropertyId instance` | `PropertyId`列挙型を使用して設定 |
| E002 | Azure Speech SDK | 話者分離の設定エラー | `enable_diarization()`メソッドが存在しない | `set_property("SpeechServiceConnection_EnableDiarization", "true")`を使用して設定 | エラー：`'SpeechConfig' object has no attribute 'enable_diarization'` | `set_property`メソッドに文字列としてプロパティ名を渡すように修正 |
| E003 | Azure Speech SDK | 話者分離の設定エラー | `property_id value must be PropertyId instance` | `PropertyId`列挙型を使用して設定 | エラー：`type object 'PropertyId' has no attribute 'SpeechServiceConnection_EnableDiarization'` | 別の方法で話者分離を設定する必要あり |
| E004 | Azure Speech SDK | 話者分離の設定エラー | `type object 'PropertyId' has no attribute 'SpeechServiceConnection_EnableDiarization'` | `PropertyId`列挙型を使用して設定 | エラー：`type object 'PropertyId' has no attribute 'SpeechServiceConnection_EnableDiarization'` | Azure Speech SDKのバージョンを確認し、適切な設定方法を調査する必要あり |
| E005 | Azure Speech SDK | 話者分離の設定エラー | Azure Speech SDK 1.34.0での話者分離設定方法の変更 | `set_property("SpeechServiceConnection_EnableDiarization", "true")`を使用して設定 | エラー：`Failed to configure Speech Service: property_id value must be PropertyId instance` | 1. Azure Speech SDKのバージョンを1.35.0以上にアップグレード<br>2. アップグレード後、`enable_diarization()`メソッドの使用を試す<br>3. それでもエラーが発生する場合は、`set_property(PropertyId.SpeechServiceConnection_EnableDiarization, "true")`を試す |
| E006 | Azure Storage | SASトークンの認証エラー | BlobストレージへのアクセスでSASトークンの認証に失敗 | SASトークンの生成方法とURLの構築方法を修正 | | |
| E007 | Azure Functions | APIエンドポイントエラー | `/api/members-meetings`エンドポイントで500エラー | `Users`テーブルのクエリに`account_status`カラムを追加 | | |
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
| E023 | Python | requirements.txtの不正な文字エラー | • requirements.txtファイルに不正なUnicode文字が含まれている<br>• pip install実行時にエラーが発生 | 1. requirements.txtファイルを開き、不正なUnicode文字を削除<br>2. 正しい形式に修正<br>3. 再度pip installを実行 | ✅ エラー解消：すべてのパッケージが正常にインストールされた | 1. 必要に応じてpipをアップグレード：`python -m pip install --upgrade pip`<br>2. 新しいパッケージを追加する際は、正しい形式で記述する<br>3. コメントは`#`で始めることを確認する |
| E024 | Azure Speech SDK | 話者分離の設定エラー | Azure Speech SDK 1.43.0で`enable_diarization()`メソッドが存在しない | `set_property("SpeechServiceConnection_EnableDiarization", "true")`を使用して設定 | エラー：`'SpeechConfig' object has no attribute 'enable_diarization'` | 1. Azure Speech SDKのドキュメントを確認し、1.43.0での正しい話者分離の設定方法を調査<br>2. 必要に応じて、SDKのバージョンを変更（1.35.0に戻すか、より新しいバージョンにアップグレード） |
| E025 | Azure Functions | EventGridトリガーのバインディングエラー | 音声ファイル処理時に発生 | EventGridトリガーをHTTPトリガーに変更し、`func.HttpRequest`を使用 | ✅ エラー解消：HTTPトリガーに変更することでバインディングエラーを解決 | 1. 新しいエンドポイントのテスト 2. エラーハンドリングの確認 |
| E026 | Azure Functions | EventGridトリガーのパラメータ型エラー | EventGridトリガーで`event`パラメータの型が不正<br>エラー：`Exception binding parameter 'event'` | EventGridトリガーをHTTPトリガーに変更し、`func.HttpRequest`を使用 | ✅ エラー解消：HTTPトリガーに変更することでパラメータ型エラーを解決 | 1. 新しいエンドポイントのテスト 2. エラーハンドリングの確認 |
| E027 | Azure Functions | トリガータイプの不一致エラー | EventGridトリガーをHTTPトリガーに変更した後、`function.json`の設定とPythonの型アノテーションが不一致<br>エラー：`FunctionLoadError: cannot load the ProcessAudio function: 'event' binding type "eventGridTrigger" and dataType "None" in function.json do not match the corresponding function parameter's Python type annotation "HttpRequest"` | EventGridトリガーに戻し、`func.EventGridEvent`を使用 | ✅ エラー解消：コードの設定を確認したところ、既に正しい設定（`func.EventGridEvent`）が適用されていた | 1. テストの実行<br>2. エラーハンドリングの確認<br>3. ログ出力の確認 |
| E028 | Azure Functions | EventGridトリガーのバインディングエラー | EventGridトリガーで`event`パラメータのバインディングに失敗<br>エラー：`Exception binding parameter 'event'. Microsoft.Azure.WebJobs.Extensions.EventGrid: Unable to bind to type Newtonsoft.Json.Linq.JObject` | EventGridトリガーのパラメータ型を`func.EventGridEvent`に統一し、イベントデータを`event.get_json()`で取得 | ✅ エラー解消：コードの設定を確認したところ、既に正しい設定（`func.EventGridEvent`と`event.get_json()`）が適用されていた | 1. テストの実行<br>2. エラーハンドリングの確認<br>3. ログ出力の確認 |
| E029 | Azure Functions | EventGridトリガーのバインディングエラー | EventGridトリガーで`event`パラメータのバインディングに失敗<br>エラー：`Exception binding parameter 'event'. Microsoft.Azure.WebJobs.Extensions.EventGrid: Unable to bind to type Newtonsoft.Json.Linq.JObject` | 1. EventGridトリガーのパラメータ型を`func.EventGridEvent`に統一<br>2. イベントデータを`event.get_json()`で取得<br>3. `function.json`の設定を確認 | 修正中 | 1. テストの実行<br>2. エラーハンドリングの確認<br>3. ログ出力の確認 |
| E030 | Azure Functions | 未定義変数の使用 | 音声処理関数でmeeting_id、user_id、transcriptが未定義のまま使用 | ファイル名から会議IDとユーザーIDを抽出するロジックを追加し、文字起こし結果の整形処理を実装 | ✅ エラー解消 | テスト実行、エラーハンドリングの確認、ログ出力の確認 |
| E031 | Azure Functions | EventGridトリガーのバインディングエラー | EventGridトリガーの`event`パラメータが`Newtonsoft.Json.Linq.JObject`型にバインドできない | Azure Functionsのバージョンを1.23.0に更新し、EventGridトリガーの設定を修正 | 解決済み | テスト実行でステータスコード202を確認 |
| E032 | Azure Functions | EventGridトリガーのバインディングエラー | EventGridトリガーで`event`パラメータのバインディングに失敗<br>エラー：`Exception binding parameter 'event'. Microsoft.Azure.WebJobs.Extensions.EventGrid: Unable to bind to type Newtonsoft.Json.Linq.JObject`<br>実行ID: bc7bbb94-3ef4-4a2d-bdf0-7175e499fddb | 1. Azure FunctionsのEventGrid拡張機能を最新バージョンに更新<br>2. `function.json`の設定を確認し、必要に応じて修正<br>3. イベントデータの処理方法を`event.data`を使用するように変更<br>4. テストJSONファイルの形式を再度確認 | ✅ エラー解消：ステータスコード202（Accepted）を確認 | 1. ログ出力の確認<br>2. 音声処理の結果確認<br>3. データベースへの保存確認 |
| E033 | Azure Functions | EventGridトリガーのバインディングエラー | EventGridトリガーで`event`パラメータのバインディングに失敗<br>エラー：`Exception binding parameter 'event'. Microsoft.Azure.WebJobs.Extensions.EventGrid: Unable to bind to type Newtonsoft.Json.Linq.JObject`<br>実行ID: 8ed97f96-18f8-4495-af40-8120fdf0cc24 | ※ E031、E032と重複。既に解決済み | ✅ 重複エントリー | 次のアクション：<br>1. Azure Functionsの設定確認（host.json、拡張機能バージョン、バインディング設定）<br>2. コードの修正アプローチ（HTTPトリガーへの変更、イベントデータ取得方法の変更、型アノテーションの修正）<br>3. テストJSONの修正（イベントデータ形式、必須フィールド、データ型）<br>4. Azure Functionsの再デプロイ（ローカルテスト、本番環境デプロイ、設定再適用）<br>5. 代替アプローチの検討（BlobTrigger、タイマートリガー、キュー使用）<br>6. デバッグ情報の収集（ログ出力、エラー分析、実行コンテキスト）<br>7. Azure Functionsのバージョン管理（バージョン固定、アップグレード、依存関係更新）<br>8. 環境変数の確認（設定、値、型）<br>9. Azure Portalでの確認（Function App設定、アプリケーション設定、ログ）<br>10. サポートへの問い合わせ（Azure Functionsサポート、既知の問題確認、コミュニティフォーラム） |
| E034 | Azure Functions | EventGridトリガーのバインディングエラー | ローカル環境でのテスト実行時 | 1. host.jsonの設定を更新：<br>```json<br>{<br>  "version": "2.0",<br>  "extensions": {<br>    "eventGrid": {<br>      "maxDeliveryAttempts": 3,<br>      "eventTimeToLive": "01:00:00"<br>    }<br>  }<br>}<br>```<br>2. requirements.txtに追加：<br>```<br>azure-functions==1.17.0<br>azure-eventgrid>=4.9.0<br>```<br>3. function_app.pyの修正：<br>```python<br>@app.event_grid_trigger(arg_name="event")<br>def process_audio(event: func.EventGridEvent) -> None:<br>    data = event.get_json()<br>```<br>4. local.settings.jsonの設定追加：<br>```json<br>{<br>  "Values": {<br>    "EventGridTopicEndpoint": "your-endpoint",<br>    "EventGridTopicKey": "your-key",<br>    "EventGridConnectionString": "your-connection-string"<br>  }<br>}<br>``` | 未実行 | 1. 修正した設定でローカルテスト実行<br>2. テストJSONでエンドポイントをテスト<br>3. ログ出力を確認<br>4. 必要に応じて代替アプローチ（BlobTrigger、タイマートリガー）を検討 |
| E004 | Azure Functions | バインディングパラメータの不一致 | `FunctionLoadError: cannot load the ProcessAudio function: the following parameters are declared in function.json but not in Python` | 関数のパラメータにバインディングパラメータを追加し、適切な型アノテーションを設定 | 解決：`process_audio`関数のパラメータに`meetingsTable`と`basicInfoQuery`を追加し、型アノテーションを設定 | 関数が正常に読み込まれるようになる |
| E035 | Azure Functions | 複数トリガーの設定エラー | 1つの関数に複数のトリガー（EventGridとHTTP）を設定しようとした<br>エラー：`ValueError: A trigger was already registered to this function` | EventGridトリガーのみを残し、HTTPトリガーの設定を削除 | ✅ エラー解消：EventGridトリガーのみの設定に修正 | 1. テストの実行<br>2. エラーハンドリングの確認<br>3. ログ出力の確認 |
| E036 | Azure Functions | EventGridトリガーの404エラー | EventGridトリガーに直接HTTPリクエストを送信した際に404エラーが発生 | 1. `/admin/functions/ProcessAudio`エンドポイントを使用してテスト<br>2. テストJSONファイルを使用してイベントデータを送信<br>3. `test_trigger.py`スクリプトを使用してテスト | ✅ エラー解消：正しいエンドポイントを使用してテスト可能に | 1. テストの実行<br>2. エラーハンドリングの確認<br>3. ログ出力の確認 |
| E037 | Azure Functions | EventGridTrigger拡張機能の未インストール | `func start`実行時に「The binding type(s) 'eventGridTrigger' are not registered」エラーが発生 | 1. EventGrid拡張機能をインストール：<br>`func extensions install --package Microsoft.Azure.WebJobs.Extensions.EventGrid --version 3.3.0`<br>2. requirements.txtに以下を追加：<br>`azure-functions`<br>`azure-eventgrid`<br>3. function_app.pyでEventGridトリガーが正しく定義されていることを確認 | 未実行 | 1. 拡張機能インストール後のテスト実行<br>2. ログ出力の確認<br>3. EventGridトリガーの動作確認 |
| E038 | Azure Functions | datetime.UTCのインポートエラー | `func start`実行時に「cannot import name 'UTC' from 'datetime'」エラーが発生 | Python 3.10では`datetime.UTC`が利用不可。Python 3.11以降の機能。解決策：<br>1. `from datetime import datetime, timezone, timedelta`に変更<br>2. `UTC`の代わりに`timezone.utc`を使用<br>3. または`datetime.now(timezone.utc)`を使用 | 未実行 | 1. インポート文の修正<br>2. UTC使用箇所の修正<br>3. 動作確認 |
| E039 | Azure Functions | openai_completion_coreモジュールのインポートエラー | `func start`実行時に「No module named 'openai_completion_core'」エラーが発生 | openai_processingパッケージ内のファイルで絶対インポートを使用しているため。解決策：<br>1. 相対インポートに変更：`from .openai_completion_core import ...`<br>2. または`from openai_processing.openai_completion_core import ...`<br>3. パッケージ構造の確認と修正 | 未実行 | 1. インポート文の修正<br>2. パッケージ構造の確認<br>3. 動作確認 |
| E040 | Azure Functions | step3_remove_completion_materials関数のインポートエラー | `func start`実行時に「cannot import name 'step3_remove_completion_materials'」エラーが発生 | openai_processingパッケージ内の関数名が一致していない。解決策：<br>1. 各ステップファイルに関数が正しく定義されているか確認<br>2. 関数名の統一（step1_format_with_offset、step2_complete_incomplete_sentences等）<br>3. __init__.pyでのエクスポート確認 | 未実行 | 1. 関数定義の確認<br>2. 関数名の統一<br>3. 動作確認 |

# 技術的知見・トラブルシューティング

## トラブルシューティング一覧表

| システム | 問題 | 発生状況 | 解決方法 |
|---------|------|----------|----------|
| Azure Speech SDK | 話者分離機能の設定エラー | Azure Functions実行時 | 1. `PropertyId`の代わりに文字列リテラルを使用<br>2. `set_property_by_name`と`get_property_by_name`を使用<br>3. SDKバージョンを1.43.0に更新 |
| Azure Functions | EventGridトリガーのテスト困難 | ローカル開発時 | 1. HTTPトリガーによるシミュレーション<br>2. テスト用JSONファイルの作成<br>3. curlコマンドによるテスト実行 |
| Azure Blob Storage | 音声ファイルの形式変換 | WebMファイルアップロード時 | 1. FFmpegを使用したWAV形式への変換<br>2. 16kHz、16ビットPCM、モノラルに変換 |
| Azure SQL Database | 接続エラー | データベース操作時 | 1. 接続文字列の確認<br>2. ファイアウォール設定の確認<br>3. 認証情報の確認 |

## データベース関連

### 制約条件
- 主キー制約：`meeting_id`と`user_id`の組み合わせ
- 外部キー制約：`meeting_id`は`BasicInfo`テーブルを参照
- 一意性制約：`file_path`は一意である必要がある

### ベクトル検索実装
- Azure Cognitive Searchを使用
- 音声認識結果のテキストをベクトル化
- コサイン類似度による検索
- インデックス設計の最適化

### Azure Database Services
- Azure SQL Database
  - 適切なサービス層の選択
  - パフォーマンスチューニング
  - バックアップ戦略
- Azure Cosmos DB
  - グローバル分散
  - 低レイテンシー
  - スケーラビリティ

### フィードバック機能
- ユーザーフィードバックの収集
- 機械学習モデルの改善
- 品質指標の追跡

## エラーハンドリング改善：TranscriptionCallback

### 問題
TranscriptionCallback関数で、meeting_idがNoneの場合にTriggerLogへのINSERTが失敗する可能性がありました。

### 対策
1. meeting_idのNoneチェックを追加
2. TriggerLogへのINSERT前に必ずmeeting_idの存在確認
3. エラーメッセージの詳細化

### 実装例
```python
# meeting_id抽出後、TriggerLog INSERT前にチェックを追加
if meeting_id is None:
    logger.warning("⚠ meeting_id is None – TriggerLog insert skipped.")
else:
    execute_query(
        """
        INSERT INTO dbo.TriggerLog (
            event_type, table_name, record_id, event_time, additional_info
        ) VALUES (?, ?, ?, GETDATE(), ?)
        """,
        ("ERROR", "Meetings", meeting_id, "エラーメッセージ")
    )
```

### 改善点
1. 安全性の向上
   - meeting_idの存在確認によるエラー防止
   - ログ出力の安定化

2. デバッグ性の向上
   - 詳細なエラーメッセージ
   - ログレベルに応じた出力

3. 運用性の向上
   - エラー発生時の追跡が容易に
   - システム状態の可視化

### 注意事項
- meeting_idの抽出に失敗した場合は、必ずログに記録
- TriggerLogへのINSERTは、meeting_idが有効な場合のみ実行
- エラーメッセージは具体的な内容を含める

## FunctionApp側でのOpenAI処理自動化実装

### 概要
Azure Speech文字起こし完了後に、FunctionApp側で自動的にOpenAI整形処理を実行し、結果をConversationSegmentsテーブルに保存する実装。

### 実装場所
- `function_app.py` の `transcription_callback` 関数内

### 処理フロー
1. **Azure Speech文字起こし** → Meetingsテーブルにtranscript_text保存
2. **OpenAI処理自動実行** → `clean_and_complete_conversation()`で整形
3. **整形結果をConversationSegmentsテーブルに反映**

### 主要な修正内容

#### 1. OpenAI処理の組み込み
```python
# transcript_textが存在すれば処理
if transcript_text and transcript_text.strip():
    # OpenAI処理を実行
    processed_text = clean_and_complete_conversation(load_transcript_segments(meeting_id))
    
    if processed_text and processed_text.strip():
        # 既存のセグメントを削除
        execute_query("DELETE FROM dbo.ConversationSegments WHERE meeting_id = ?", (meeting_id,))
        
        # 整形結果をセグメント化してDBに保存
        segments = []
        for line in processed_text.splitlines():
            m = re.match(r"Speaker(\d+):(.+)", line)
            if m:
                segments.append({
                    "speaker": int(m.group(1)),
                    "text": m.group(2).strip()
                })
```

#### 2. エラーハンドリングの強化
- `transcript_text`がNoneまたは空の場合のスキップ処理
- OpenAI処理結果が空の場合の検知
- 想定外の形式の行の検知とログ出力
- OpenAI処理失敗時の非致命的エラー処理（元の文字起こし結果を使用）

#### 3. ログ出力の改善
- transcript_textの長さと先頭100文字の表示
- 処理結果の行数とセグメント化された行数の表示
- 想定外の形式の行の警告ログ
- 各段階での詳細なログ出力

### テスト用スクリプト
`test_openai_pipeline.py`を作成し、FunctionAppを通さずに直接OpenAI処理をテスト可能。

```bash
# meeting_id指定でテスト
python test_openai_pipeline.py --meeting-id 123

# 直接テキストでテスト
python test_openai_pipeline.py --text "Speaker1: こんにちは\nSpeaker2: はい"
```

### 注意点
- OpenAI処理の失敗は致命的ではないため、処理を継続
- 既存のセグメントは削除してOpenAI処理結果で置き換え
- 時間情報は簡易的に順番に1秒ずつ設定
- 話者情報は既存のものを再利用、なければ新規作成

### 関連ファイル
- `function_app.py`: メイン実装
- `openai_completion_core.py`: OpenAI処理のコア機能
- `test_openai_pipeline.py`: テスト用スクリプト

## Azure Speech 処理

### FuncApp_MTG処理変更（2024年12月）

#### 変更内容
Azure Speech の channel_0.json をもとに、Meetings.transcript_text に保存する形式を変更。

#### 出力フォーマット
```
(Speaker1)[こんにちは、よろしくお願いします。](12.5) (Speaker2)[ありがとうございます。](17.2) ...
```

#### 処理内容
1. **channel_0.json の "recognizedPhrases" をループ**
2. **各セグメントから以下を抽出：**
   - 話者番号：`speaker`
   - 発言内容：`nBest[0]["display"]`
   - 開始時刻（秒）：`offset`（ISO 8601）→ `isodate.parse_duration` で秒数に変換
3. **形式で文字列を生成：**
   ```python
   (Speaker{n})[{テキスト}]({秒数})
   ```
4. **各セグメントを " "（半角スペース）で結合して 1行に整形**
5. **Meetings.transcript_text に保存**

#### 実装詳細
- `isodate`ライブラリを使用してISO 8601形式の時刻を秒数に変換
- 秒数は小数第1位まで表示（例：12.5）
- 改行はせず、すべてのセグメントを連結して1行にまとめる
- エラーハンドリング：時刻変換に失敗した場合は0.0秒として処理

#### 変更箇所
- `AzureFunctions-Python-SpeakerDiarization/function_app.py`
- `recognizedPhrases`の処理部分（817行目付近）
- `isodate`ライブラリのインポート追加

#### 技術的ポイント
- ISO 8601形式の時刻文字列（例：PT12.5S）を秒数に変換
- `isodate.parse_duration()`でDurationオブジェクトを取得
- `total_seconds()`で秒数を取得し、`round(seconds, 1)`で小数第1位まで表示

### 会話整形ステップでのoffset表記保持（2024年12月）

#### 変更内容
ステップ1・2・3において、各行の末尾に記載されているoffset（例：(12.5)）を削除せず、常に保持する処理に統一。

#### 対象ファイル
- `openai_completion_step1.py`
- `openai_completion_step2.py`
- `openai_completion_step3.py`

#### 処理ルール
1. **各行の末尾にある `(<数値>)` を offset として一時保持**
   - 例：`Speaker1: こんにちは。(12.5)` の `(12.5)` 部分

2. **本文の整形処理後も、元の offset をそのまま再付与**
   - offset を誤って変形・削除・統合しないようにする

3. **実装参考（正規表現）**
   ```python
   import re
   
   match = re.match(r"(Speaker\d+: .+?)(\(\d+(\.\d+)?\))$", line)
   if match:
       body = match.group(1)    # ex. 'Speaker1: こんにちは。'
       offset = match.group(2)  # ex. '(12.5)'
       cleaned_body = clean_text(body)
       final_line = cleaned_body + offset
   else:
       final_line = clean_text(line)  # fallback（offsetなし行）
   ```

#### ステップ1の実装詳細
- **入力仕様**: `(Speaker1)[こんにちは、よろしくお願いします。](12.5) (Speaker2)[ありがとうございます。](17.2)`
- **出力フォーマット**: 
  ```
  Speaker1: こんにちは、よろしくお願いします。(12.5)
  Speaker2: ありがとうございます。(17.2)
  ```
- **処理内容**:
  1. `parse_transcript_text()`: Meetings.transcript_textをパース
  2. `format_segments_with_offset()`: offset表記付きの形式に整形
  3. `step1_format_with_offset()`: メイン処理関数

#### ステップ2・3の実装詳細
- **文字列ベースの処理に変更**: セグメントリストから文字列ベースの処理に変更
- **offset分離・再付与**: `extract_offset_from_line()`でoffsetを分離し、処理後に再付与
- **後方互換性**: 既存のセグメントリスト処理関数も残して後方互換性を保持

#### 技術的ポイント
- 正規表現 `r"(Speaker\d+: .+?)(\(\d+(\.\d+)?\))$"` でoffsetを抽出
- 処理前後でoffsetを一時保存し、処理後に再付与
- 小数の末尾の `.0` を削る必要はなし（12.0 でも可）
- エラーハンドリング：offset抽出に失敗した場合は元の行をそのまま保持

#### 変更箇所
- `openai_completion_step1.py`: 新機能追加
- `openai_completion_step2.py`: 文字列ベース処理に変更
- `openai_completion_step3.py`: 文字列ベース処理に変更

### 会話整形ステップ4・5でのoffset保持（2024年12月）

#### 変更内容
ステップ4・5において、会話が前後の行に統合（吸収）される場合でも、もともとのoffsetを正しく保持した状態で出力するように処理を変更。

#### 対象ファイル
- `openai_completion_step4.py`
- `openai_completion_step5.py`

#### 処理仕様
**吸収が発生する例**:
```
Speaker1: えっと、40分。(12.5)  
Speaker1: はい、大丈夫です。(13.8)
```

**統合後（正しい出力）**:
```
Speaker1: えっと、40分。はい、大丈夫です。(12.5)
```
※ offsetは先頭行（吸収元）の値を保持し、吸収された側のoffsetは破棄

#### 修正内容
1. **各行の末尾 `(<数値>)` を正規表現で抽出し、offset値として保持**
2. **会話統合が発生する場合**:
   - 結合対象行の本文を前の行に追加
   - offsetは結合元（先頭の行）のものを維持
   - 統合されたあとの行は出力しない or スキップ

#### 実装詳細
- **offset抽出関数**: `extract_offset_from_line()`で正規表現 `r"(Speaker\d+: .+?)\(([\d.]+)\)$"` を使用
- **統合処理**: 先頭行のoffsetを保持し、統合される行のoffsetは破棄
- **文字列ベース処理**: セグメントリストから文字列ベースの処理に変更
- **後方互換性**: 既存のセグメントリスト処理関数も残して後方互換性を保持

#### ステップ4の実装詳細
- **括弧付きセグメントの吸収処理**: `merge_backchannel_with_next_text()`でoffset保持
- **吸収元のoffset維持**: 前の行（吸収元）のoffsetを保持し、括弧付きセグメントのoffsetは破棄
- **エラーハンドリング**: offset抽出に失敗した場合は元の行をそのまま保持

#### ステップ5の実装詳細
- **同一話者の発言連結処理**: `merge_same_speaker_segments_text()`でoffset保持
- **先頭行のoffset維持**: 連続する同じ話者の行を結合する際、先頭行のoffsetを保持
- **統合行のoffset破棄**: 統合される行のoffsetは破棄し、先頭行のoffsetのみを使用

#### 技術的ポイント
- 正規表現 `r"(Speaker\d+: .+?)\(([\d.]+)\)$"` でoffsetを抽出
- 統合処理では先頭行（吸収元）のoffsetを優先
- 統合される行のoffsetは破棄して、先頭行のoffsetのみを保持
- エラーハンドリング：offset抽出に失敗した場合は元の行をそのまま保持

#### 注意点
- 吸収の対象外（話者違い or 時間間隔が大きいなど）の場合は、統合せずそのまま出力
- offsetがない／壊れている行についてはログ警告 or スキップで問題なし
- 後方互換性のため、既存のセグメントリスト処理関数も残存

#### 変更箇所
- `openai_completion_step4.py`: 文字列ベース処理に変更、offset保持機能追加
- `openai_completion_step5.py`: 文字列ベース処理に変更、offset保持機能追加

### 会話整形ステップ6でのoffset保持（2024年12月）

#### 変更内容
ステップ6において、フィラー削除処理を行う際に、各行の末尾に記載されているoffset（例：(12.5)）を削除せず、常に保持するように処理を変更。

#### 対象ファイル
- `openai_completion_step6.py`

#### 処理仕様
**入力例**:
```
Speaker1: えっと、40分の会議ですね。(12.5)
Speaker2: あの、はい、大丈夫です。(13.8)
```

**出力例**:
```
Speaker1: 40分の会議ですね。(12.5)
Speaker2: はい、大丈夫です。(13.8)
```
※ フィラー（「えっと」「あの」）が削除されるが、offsetは保持される

#### 修正内容
1. **各行の末尾 `(<数値>)` を正規表現で抽出し、offset値として保持**
2. **フィラー削除処理**:
   - 本文のみをOpenAI APIでフィラー削除処理
   - offsetは元の値をそのまま保持
   - 処理後にoffsetを再付与

#### 実装詳細
- **offset抽出関数**: `extract_offset_from_line()`で正規表現 `r"(Speaker\d+: .+?)\(([\d.]+)\)$"` を使用
- **フィラー削除処理**: `remove_fillers_from_text_with_offset()`でoffset保持
- **文字列ベース処理**: セグメントリストから文字列ベースの処理に変更

### ConversationSegment挿入処理の修正（2024年12月）

#### 変更内容
OpenAIにより整形済みとなった会話データ（offset付き）をFunctionApp側で受け取り、ConversationSegmentテーブルへ挿入する処理を追加・修正。

#### 対象ファイル
- `function_app.py`

#### 処理対象
ConversationSegmentテーブルへのINSERT部分

#### 入力データ形式
```
Speaker1: はい、大丈夫です。(12.5)
Speaker2: お願いします。(17.2)
```

#### 抽出項目
| 項目 | 取得元 | 備考 |
|------|--------|------|
| speaker_id | Speaker{n} | n を整数として抽出 |
| text | 冒頭の SpeakerX: を除いた本文部分 | 末尾の offset も除外 |
| start_time | (...) の中の秒数（float） | ISO 8601 に変換しない秒形式 |
| end_time | NULL | 今回は offset のみで duration 不明のため |
| duration | 0（固定値） | 固定で 0 を設定 |

#### 実装詳細
- **正規表現**: `r"Speaker(\d+): (.+)\(([\d.]+)\)$"` でoffset付きの形式を解析
- **データ抽出**: speaker_id、text、start_timeを正しく抽出
- **後方互換性**: offsetなしの行も簡易解析で処理
- **エラーハンドリング**: 解析不可能な行はスキップして警告ログを出力

#### 技術的ポイント
- 正規表現でoffset付きの形式を正確に解析
- start_timeはfloat型で保存（秒単位）
- end_timeはNULL、durationは0（固定値）を設定
- 解析不可能な行はスキップして処理を継続

#### 注意点
- データが壊れている（offsetがない等）場合はスキップして警告ログを出す
- 整形済みテキストはlist形式または1行ごとの配列で渡されることを想定
- 後方互換性のため、offsetなしの行も簡易解析で処理

#### 変更箇所
- `function_app.py`: ConversationSegment挿入処理の修正

## データベース

### Azure Blob Storage SASトークン付きURL生成機能

#### 実装概要
プライベートコンテナに設定されたAzure Blob Storageの音声ファイルに、フロントエンドから直接アクセスできるようにSASトークン付きURLを生成する機能を実装。

#### 修正内容

##### 1. バックエンド（Azure Functions Python API）
**ファイル**: `AzureFunctions-Python-api/function_app.py`

**追加したインポート**:
```python
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
```

**追加した関数**:
```python
def generate_sas_url(container_name: str, blob_name: str) -> str:
    """
    Blob StorageのSASトークン付きURLを生成する
    
    Args:
        container_name (str): コンテナ名
        blob_name (str): ブロブ名（ファイルパス）
        
    Returns:
        str: SASトークン付きURL
    """
    account_name = "audiosalesanalyzeraudio"
    account_key = os.environ.get("AZURE_STORAGE_KEY")

    if not account_key:
        raise Exception("AZURE_STORAGE_KEY is not set")

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )

    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
```

**修正した関数**: `get_conversation_segments_by_meeting_id`
- データベースから取得したセグメントに対して、各セグメントの`file_path`を使用してSASトークン付きURLを生成
- 生成したURLを`audio_path`フィールドとして追加

```python
# 各セグメントに対して SAS付きURLを生成して追加
for segment in segments:
    file_path = segment.get("file_path")
    if file_path:
        segment["audio_path"] = generate_sas_url("moc-audio", file_path)
    else:
        segment["audio_path"] = ""
```

**依存関係追加**: `requirements.txt`
```
azure-storage-blob
```

##### 2. フロントエンド（Next.js）

**型定義修正**: `next-app/src/types/index.ts`
```typescript
export interface ConversationSegment {
  // ... existing fields ...
  audio_path?: string  // SASトークン付きURL
  // ... existing fields ...
}
```

**コンポーネント修正**:
- `AudioSegmentPlayer.tsx`: 環境変数からURL構築する処理を削除し、`audioPath`を直接使用
- `AudioController.tsx`: 同様に環境変数からURL構築する処理を削除
- `ChatMessage.tsx`: `segment.audio_path`を使用するように修正
- `feedback/[meeting_id]/page.tsx`: `segment.audio_path`を使用するように修正

### APIレスポンス例
```json
{
  "success": true,
  "segments": [
    {
      "segment_id": 1,
      "file_path": "meeting_88_user_34_2025-05-21T07-18-44-213.wav",
      "audio_path": "https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_88_user_34_2025-05-21T07-18-44-213.wav?<SAS_TOKEN>",
      "content": "こんにちは、よろしくお願いします。",
      "speaker_name": "営業担当",
      "speaker_role": "Sale",
      "start_time": 0.0,
      "end_time": 3.5,
      "duration_seconds": 3,
      "status": "completed",
      "inserted_datetime": "2025-01-21T07:18:44.213Z",
      "updated_datetime": "2025-01-21T07:18:44.213Z"
    }
  ]
}
```

### 環境変数設定
**Azure App Settings**:
- `AZURE_STORAGE_KEY`: Azure Blob Storageのアカウントキー

**local.settings.json**:
```json
{
  "Values": {
    "AZURE_STORAGE_KEY": "your-storage-account-key"
  }
}
```

### セキュリティ考慮事項
1. **SASトークンの有効期限**: 1時間に設定（必要に応じて調整可能）
2. **権限**: 読み取り専用（`BlobSasPermissions(read=True)`）
3. **アカウントキー**: 環境変数で管理し、コードにハードコーディングしない
4. **コンテナ**: プライベートコンテナを使用し、SASトークンでのみアクセス可能

### 利点
1. **セキュリティ**: プライベートコンテナを維持しながら、一時的なアクセスを提供
2. **パフォーマンス**: フロントエンドで直接Blob Storageにアクセス可能
3. **スケーラビリティ**: サーバーを経由せずに音声ファイルを配信
4. **コスト効率**: サーバーの帯域幅を使用しない

### 注意点
1. **SASトークンの有効期限管理**: 1時間後に再取得が必要
2. **エラーハンドリング**: `AZURE_STORAGE_KEY`が未設定の場合の適切なエラー処理
3. **ファイルパスの存在確認**: `file_path`が空の場合の処理
4. **フロントエンドの型安全性**: `audio_path`がオプショナルフィールドとして定義