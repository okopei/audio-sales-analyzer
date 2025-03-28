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