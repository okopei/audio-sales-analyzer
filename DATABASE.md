# データベース設計

## テーブル構成

### 1. Users（ユーザー管理）
```sql
CREATE TABLE Users (
    id              UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    email           NVARCHAR(255) UNIQUE NOT NULL,
    hashed_password NVARCHAR(255) NOT NULL,
    full_name       NVARCHAR(100),
    company_name    NVARCHAR(100),
    created_at      DATETIME2 DEFAULT GETUTCDATE(),
    updated_at      DATETIME2 DEFAULT GETUTCDATE()
);
```

### 2. AudioRecordings（音声データ）
```sql
CREATE TABLE AudioRecordings (
    id              UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    user_id         UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Users(id),
    title           NVARCHAR(255),
    description     NVARCHAR(MAX),
    audio_url       NVARCHAR(255),  -- Azure Blob Storage URL
    duration        INT,            -- 秒単位
    file_size       BIGINT,         -- バイト単位
    created_at      DATETIME2 DEFAULT GETUTCDATE(),
    updated_at      DATETIME2 DEFAULT GETUTCDATE()
);
```

### 3. Transcriptions（文字起こしデータ）
```sql
CREATE TABLE Transcriptions (
    id                  UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    audio_recording_id  UNIQUEIDENTIFIER FOREIGN KEY REFERENCES AudioRecordings(id),
    full_text          NVARCHAR(MAX),
    language           NVARCHAR(10),
    confidence_score   FLOAT,
    vector_json        NVARCHAR(MAX),  -- OpenAI Ada-2のベクトルをJSON形式で保存
    created_at         DATETIME2 DEFAULT GETUTCDATE(),
    updated_at         DATETIME2 DEFAULT GETUTCDATE()
);
```

### 4. TranscriptionSegments（文字起こしセグメント）
```sql
CREATE TABLE TranscriptionSegments (
    id                  UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    transcription_id    UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Transcriptions(id),
    start_time         FLOAT,
    end_time           FLOAT,
    text               NVARCHAR(MAX),
    speaker_label      NVARCHAR(50),
    confidence_score   FLOAT,
    created_at         DATETIME2 DEFAULT GETUTCDATE()
);
```

### 5. Tags（タグ管理）
```sql
CREATE TABLE Tags (
    id          UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name        NVARCHAR(50) UNIQUE NOT NULL,
    created_at  DATETIME2 DEFAULT GETUTCDATE()
);
```

### 6. AudioTags（音声とタグの関連付け）
```sql
CREATE TABLE AudioTags (
    audio_recording_id  UNIQUEIDENTIFIER FOREIGN KEY REFERENCES AudioRecordings(id),
    tag_id             UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Tags(id),
    created_at         DATETIME2 DEFAULT GETUTCDATE(),
    PRIMARY KEY (audio_recording_id, tag_id)
);
```

### 7. AudioRatings（音声評価データ）
```sql
CREATE TABLE AudioRatings (
    id                  UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    audio_recording_id  UNIQUEIDENTIFIER FOREIGN KEY REFERENCES AudioRecordings(id),
    rating             FLOAT,           -- 評価スコア（例：1.0 ～ 5.0）
    rated_by           UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Users(id),
    comment            NVARCHAR(MAX),   -- 評価コメント
    created_at         DATETIME2 DEFAULT GETUTCDATE()
);
```

### 8. TagRatings（タグ評価データ）
```sql
CREATE TABLE TagRatings (
    id          UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    tag_id      UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Tags(id),
    rating      FLOAT,           -- 評価スコア（例：1.0 ～ 5.0）
    rated_by    UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Users(id),
    comment     NVARCHAR(MAX),   -- 評価コメント
    created_at  DATETIME2 DEFAULT GETUTCDATE()
);
```

## Azure Cognitive Search インデックス設計

```json
{
  "name": "transcriptions-index",
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "searchable": false
    },
    {
      "name": "full_text",
      "type": "Edm.String",
      "searchable": true,
      "analyzer": "ja.microsoft"
    },
    {
      "name": "vector_embedding",
      "type": "Collection(Edm.Single)",
      "dimensions": 1536,
      "vectorSearchConfiguration": "default"
    },
    {
      "name": "created_at",
      "type": "Edm.DateTimeOffset",
      "filterable": true,
      "sortable": true
    },
    {
      "name": "rating_score",
      "type": "Edm.Double",
      "filterable": true,
      "sortable": true,
      "searchable": false
    },
    {
      "name": "tag_ratings",
      "type": "Collection(Edm.Double)",
      "filterable": true,
      "sortable": false,
      "searchable": false
    }
  ],
  "vectorSearch": {
    "algorithmConfigurations": [
      {
        "name": "default",
        "kind": "hnsw"
      }
    ]
  },
  "scoringProfiles": [
    {
      "name": "weightedScore",
      "functions": [
        {
          "type": "magnitude",
          "fieldName": "rating_score",
          "boost": 1.5,
          "interpolation": "linear"
        },
        {
          "type": "magnitude",
          "fieldName": "tag_ratings",
          "boost": 2.0,
          "interpolation": "linear"
        }
      ]
    }
  ]
}
```

## 主な変更点

1. **ベクトルデータの扱い**
   - データベースではJSONとして保存
   - 検索機能はAzure Cognitive Searchで実現

2. **その他の最適化**
   - SQL Serverの機能を活用
   - DEFAULT制約にGETUTCDATE()を使用
   - FOREIGN KEY構文の変更

## 主な機能と利点

1. **ベクトル検索機能**
   - Transcriptionsテーブルのvector_embeddingカラムを使用
   - Azure Cognitive Searchでセマンティック検索が可能
   - 類似コンテンツの検索や推薦が可能

2. **セグメント分析**
   - 音声の特定部分へのジャンプが可能
   - 話者ごとの分析が可能
   - タイムスタンプベースの検索

3. **タグ付けシステム**
   - 柔軟な分類が可能
   - 複数のタグを付与可能
   - タグベースの検索と整理

4. **ユーザー管理**
   - 基本的な認証機能
   - 企業ごとのデータ管理
   - アクセス制御

5. **評価機能**
   - 音声に対するマネージャーによる評価
   - 評価スコアとコメントの保存
   - 評価に基づく検索とランキング

## スケーラビリティ
- UNIQUEIDENTIFIERを使用して水平スケーリングに対応
- ベクトルデータの効率的な検索
- Blob Storageによる大容量音声データの管理

## セキュリティ
- パスワードのハッシュ化
- 外部キー制約によるデータ整合性の確保
- Azure Key Vaultでの機密情報管理

## テーブルの詳細な役割説明

### 1. Users（ユーザー管理）
- ユーザーの基本情報を管理
- メールアドレスとパスワードによる認証
- 企業名も保持できるため、組織単位での管理が可能
- 作成日時と更新日時を記録して変更履歴を追跡

### 2. AudioRecordings（音声データ）
- 録音された音声ファイルの基本情報を管理
- 実際の音声ファイルはAzure Blob Storageに保存し、URLで参照
- タイトルや説明文で音声の内容を管理
- ファイルサイズや再生時間などの技術情報も保持
- ユーザーIDと紐付けて、誰の録音かを管理

### 3. Transcriptions（文字起こしデータ）
- 音声から変換されたテキストデータを管理
- 音声全体の文字起こし結果を保持
- ベクトル埋め込み（vector_embedding）で類似検索を可能に
- 言語情報や信頼度スコアも保持
- AudioRecordingsと1対1で紐付け

### 4. TranscriptionSegments（文字起こしセグメント）
- 文字起こしを時間単位で細かく分割して管理
- 開始時間と終了時間で特定の部分を参照可能
- 話者ラベルで誰が話しているかを識別
- 各セグメントごとの信頼度スコアを保持
- Transcriptionsと1対多で紐付け

### 5. Tags（タグ管理）
- 音声データを分類するためのタグを管理
- タグ名の重複を防ぐためにUNIQUE制約
- 例：「営業会議」「顧客ヒアリング」「商品説明」など
- シンプルな構造で効率的なタグ管理

### 6. AudioTags（音声とタグの関連付け）
- AudioRecordingsとTagsの中間テーブル
- 多対多の関係を実現（1つの音声に複数のタグ、1つのタグを複数の音声に）
- 作成日時を記録してタグ付けの履歴を追跡
- 複合主キーで重複を防止

### 7. AudioRatings（音声評価データ）
- 音声に対するマネージャーによる評価
- 評価スコアとコメントの保存
- 評価に基づく検索とランキング

### 8. TagRatings（タグ評価データ）
- タグに対するマネージャーによる評価
- タグごとの評価スコアとコメントの保存
- タグベースの検索と整理

## テーブル連携の利点
1. ユーザーごとの音声データ管理
2. 詳細な文字起こしデータの保存と検索
3. 柔軟なタグ付けと分類
4. 時系列での分析
5. セキュアなアクセス制御

## データの保存と処理フロー

### 音声データの保存構造
```
[音声ファイル]
    ↓
[Azure Blob Storage] ← URLを保存 ← [AudioRecordings テーブル]
```

### 文字起こし処理フロー
```
[音声ファイル from Blob Storage]
    ↓
[Azure Speech Services]で文字起こし
    ↓
[Transcriptions テーブル] ← 全体の文字起こしテキスト
    ↓
[Azure Cognitive Search] ← ベクトル検索用インデックス
    ↓
[TranscriptionSegments テーブル] ← 時間区切りの詳細データ
```

### 評価データの処理フロー
```
[マネージャーによる評価]
    ↓
[AudioRatings テーブル] ← 音声ごとの評価スコアと評価コメント
    ↓
[Azure Cognitive Search] ← インデックス更新
    ↓
[検索結果] ← 音声評価を考慮したランキング
```

### タグ評価の処理フロー
```
[マネージャーによるタグ評価]
    ↓
[TagRatings テーブル] ← タグごとの評価スコアと評価コメント
    ↓
[音声データの検索時]
    ↓
[関連するタグの評価スコアを集計]
    ↓
[Azure Cognitive Search] ← インデックス更新
    ↓
[検索結果] ← 音声評価とタグ評価の両方を考慮したランキング
```
