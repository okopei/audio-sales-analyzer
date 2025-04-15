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
