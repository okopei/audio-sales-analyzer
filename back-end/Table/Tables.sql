-- ユーザー管理
CREATE TABLE Users (
    -- 基本情報
    user_id INT PRIMARY KEY IDENTITY(1,1),
    user_name VARCHAR(50) NOT NULL,
    email VARCHAR(256) NOT NULL UNIQUE,
    password_hash NVARCHAR(128) NOT NULL,  -- ハッシュ化されたパスワード
    salt NVARCHAR(36) NOT NULL,            -- パスワードソルト

    -- アカウント状態
    is_active BIT DEFAULT 1,
    account_status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, LOCKED, SUSPENDED など
    last_login_datetime DATETIME,

    -- 監査情報
    inserted_datetime DATETIME DEFAULT GETDATE(),
    updated_datetime DATETIME DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,        -- 論理削除用

    -- アカウント管理
    password_reset_token VARCHAR(100) NULL,
    password_reset_expires DATETIME NULL,
    login_attempt_count INT DEFAULT 0,
    is_manager BIT NULL,
    manager_id INT NULL
)

-- 基本情報テーブル
CREATE TABLE BasicInfo (
    meeting_id INT IDENTITY(1,1) PRIMARY KEY,          -- 会議の一意識別子（主キー）
    user_id INT NOT NULL,                              -- ユーザーID
    meeting_datetime DATETIME NOT NULL,                -- 実施日時
    client_company_name NVARCHAR(100) NOT NULL,        -- 顧客企業名
    client_contact_name NVARCHAR(50) NOT NULL,         -- 担当者名
    industry_type NVARCHAR(50)  NULL,               -- 業種
    company_scale NVARCHAR(50)  NULL,               -- 規模
    sales_goal NVARCHAR(500)  NULL,                 -- 商談ゴール
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,                    -- 論理削除用

    CONSTRAINT FK_BasicInfo_Users
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- 会議情報（音声データと文字起こし情報を統合）
CREATE TABLE Meetings (
    meeting_id INT NOT NULL,                          -- BasicInfoテーブルを参照する外部キー
    user_id INT NOT NULL,                             -- 作成したユーザーID
    title NVARCHAR(255) NOT NULL,                     -- 会議タイトル
    file_name NVARCHAR(200) NOT NULL,                 -- 音声ファイル名
    file_path NVARCHAR(1000) NOT NULL,                -- 音声ファイルパス
    file_size BIGINT NOT NULL,                        -- ファイルサイズ（バイト）
    duration_seconds INT NOT NULL DEFAULT 0,          -- 音声時間（秒）
    status NVARCHAR(50) NOT NULL DEFAULT 'processing', -- 処理状態
    transcript_text NVARCHAR(MAX) NULL,               -- 文字起こし結果
    error_message NVARCHAR(MAX) NULL,                 -- エラーメッセージ
    client_company_name NVARCHAR(100) NOT NULL,       -- 顧客企業名
    client_contact_name NVARCHAR(50) NOT NULL,        -- 担当者名
    meeting_datetime DATETIME NOT NULL,               -- 会議実施日時
    start_datetime DATETIME NOT NULL,                 -- 処理開始日時
    end_datetime DATETIME NULL,                       -- 処理完了日時
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,                   -- 論理削除用

    CONSTRAINT PK_Meetings PRIMARY KEY (meeting_id, user_id),  
    CONSTRAINT UK_Meetings_MeetingID UNIQUE (meeting_id),  
    CONSTRAINT FK_Meetings_Users
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT FK_Meetings_BasicInfo
        FOREIGN KEY (meeting_id) REFERENCES BasicInfo(meeting_id)
)

-- 話者マスタ
CREATE TABLE Speakers (
    speaker_id INT PRIMARY KEY IDENTITY(1,1),         -- 話者の一意識別子
    speaker_name NVARCHAR(50) NOT NULL,               -- 話者名
    speaker_role NVARCHAR(100),                       -- 話者の役割（例：営業、顧客など）
    user_id INT NULL,                                 -- ユーザーと紐付く場合のみ設定
    meeting_id INT NULL,                              -- 関連する会議ID
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT FK_Speakers_Users
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT FK_Speakers_Meetings
        FOREIGN KEY (meeting_id) REFERENCES BasicInfo(meeting_id)
)

-- ミーティングメモ（文字起こし結果を含む）
CREATE TABLE ConversationSegments (
    segment_id INT PRIMARY KEY IDENTITY(1,1),        -- セグメントの一意識別子
    user_id INT NULL,                                -- 作成者（NULL許容）
    speaker_id INT NOT NULL,                         -- 発言者
    meeting_id INT NOT NULL,                         -- 関連する会議ID
    content NVARCHAR(MAX),                           -- 文字起こし内容
    file_name NVARCHAR(200) NOT NULL,                -- 音声ファイル名
    file_path NVARCHAR(1000) NOT NULL,               -- 音声ファイルパス
    file_size BIGINT NOT NULL,                       -- ファイルサイズ（バイト）
    duration_seconds INT NOT NULL DEFAULT 0,          -- 音声時間（秒）
    status NVARCHAR(50) NOT NULL DEFAULT 'processing', -- 処理状態（waiting, processing, completed, error）
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    start_time FLOAT NULL,
    end_time FLOAT NULL
    
    CONSTRAINT FK_ConversationSegments_Users 
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT FK_ConversationSegments_Speakers
        FOREIGN KEY (speaker_id) REFERENCES Speakers(speaker_id),
    CONSTRAINT FK_ConversationSegments_Meetings
        FOREIGN KEY (meeting_id) REFERENCES Meetings(meeting_id)
)

-- コメントテーブル
CREATE TABLE Comments (
    comment_id INT PRIMARY KEY IDENTITY(1,1),         -- コメントの一意識別子
    segment_id INT NOT NULL,                          -- 関連するセグメントID
    meeting_id INT NOT NULL,                          -- 関連する会議ID
    user_id INT NOT NULL,                             -- コメント投稿者のユーザーID
    content NVARCHAR(MAX) NOT NULL,                   -- コメント内容
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,                    -- 論理削除用
    
    CONSTRAINT FK_Comments_ConversationSegments
        FOREIGN KEY (segment_id) REFERENCES ConversationSegments(segment_id),
    CONSTRAINT FK_Comments_Meetings
        FOREIGN KEY (meeting_id) REFERENCES Meetings(meeting_id),
    CONSTRAINT FK_Comments_Users
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
)

-- コメント既読状態管理
CREATE TABLE CommentReads (
    comment_id INT NOT NULL,                          -- 既読されたコメントID
    reader_id INT NOT NULL,                           -- 既読したユーザーID
    read_datetime DATETIME NOT NULL DEFAULT GETDATE(), -- 既読した日時
    
    CONSTRAINT PK_CommentReads PRIMARY KEY (comment_id, reader_id),
    CONSTRAINT FK_CommentReads_Comments
        FOREIGN KEY (comment_id) REFERENCES Comments(comment_id),
    CONSTRAINT FK_CommentReads_Users
        FOREIGN KEY (reader_id) REFERENCES Users(user_id)
)

CREATE TABLE dbo.ConversationEnrichmentSegments (
    id INT IDENTITY(1,1) PRIMARY KEY,              -- 自動採番の主キー
    meeting_id INT NOT NULL,                       -- 会議ID（外部キー）
    line_no INT NOT NULL,                          -- セグメント行番号（ステップ1で付与）

    speaker INT NOT NULL,                          -- 話者番号
    transcript_text_segment NVARCHAR(MAX) NOT NULL,-- ステップ1で分割された発話テキスト

    is_filler BIT NOT NULL DEFAULT 0,              -- 「10文字未満の発話」か（True=つなぎ表現）

    front_score FLOAT NULL,                        -- ステップ2：前の発話との接続自然度スコア
    after_score FLOAT NULL,                        -- ステップ2：後の発話との接続自然度スコア

    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),  -- 登録日時
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),   -- 更新日時
    revised_text_segment NVARCHAR(MAX) NULL,                -- ステップ2で修正された発話テキスト
    delete_candidate_word NVARCHAR(MAX) NULL,               -- ステップ2で削除候補の単語

    CONSTRAINT FK_ConversationEnrichmentSegments_Meetings
        FOREIGN KEY (meeting_id) REFERENCES dbo.Meetings(meeting_id)
)

CREATE TABLE dbo.ConversationMergedSegments (
    id INT IDENTITY(1,1) PRIMARY KEY,              -- 自動採番主キー
    meeting_id INT NOT NULL,                       -- 会議ID（外部キー）
    line_no INT NOT NULL,                          -- 対象行番号

    speaker INT NOT NULL,                          -- 話者番号
    original_text NVARCHAR(MAX) NOT NULL,          -- 元のtranscript_text_segment
    merged_text NVARCHAR(MAX) NOT NULL,            -- delete_candidate除去＋revised_text追加済みの最終文

    source_segment_ids NVARCHAR(100) NULL,         -- 元データの line_no（例: "12,13"）

    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),  -- 作成日時
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),   -- 更新日時
    cleaned_text NVARCHAR(MAX) NULL,                       -- フィラー削除後のテキスト
    summary NVARCHAR(MAX) NULL,                       -- 要約タイトル
    CONSTRAINT FK_ConversationMergedSegments_Meetings
        FOREIGN KEY (meeting_id) REFERENCES dbo.Meetings(meeting_id)
);

CREATE TABLE dbo.ConversationFinalSegments (
    id INT IDENTITY(1,1) PRIMARY KEY,
    meeting_id INT NOT NULL,
    speaker INT NOT NULL,
    merged_text NVARCHAR(MAX) NOT NULL,
    offset_seconds FLOAT NULL,
    inserted_datetime DATETIME DEFAULT GETDATE(),
    updated_datetime DATETIME DEFAULT GETDATE()
);

-- インデックス
CREATE INDEX idx_users_email ON Users(email)                            -- メールアドレスによる検索用

CREATE INDEX idx_meetings_user ON Meetings(user_id)                     -- ユーザーIDによる検索用
CREATE INDEX idx_meetings_datetime ON Meetings(meeting_datetime)        -- 会議日時による検索用
CREATE INDEX idx_meetings_company ON Meetings(client_company_name)      -- 顧客企業名による検索用
CREATE INDEX idx_meeting_audio_meeting ON Meetings(meeting_id)      -- 会議IDによる検索用

CREATE INDEX idx_meeting_transcript_meeting ON Meetings(meeting_id) -- 会議IDによる検索用
CREATE INDEX idx_meeting_transcript_audio ON Meetings(meeting_id)    -- 音声IDによる検索用
CREATE INDEX idx_meeting_transcript_status ON Meetings(status)     -- 状態による検索用

CREATE INDEX idx_speakers_user ON Speakers(user_id)                      -- ユーザーIDによる検索用
CREATE INDEX idx_speakers_name ON Speakers(speaker_name)                 -- 話者名による検索用

CREATE INDEX idx_conversation_segments_user ON ConversationSegments(user_id)               -- ユーザーIDによる検索用
CREATE INDEX idx_conversation_segments_speaker ON ConversationSegments(speaker_id)         -- 話者IDによる検索用
CREATE INDEX idx_conversation_segments_meeting ON ConversationSegments(meeting_id)         -- 会議IDによる検索用
CREATE INDEX idx_conversation_segments_datetime ON ConversationSegments(inserted_datetime) -- 日時による検索用

CREATE INDEX idx_basicinfo_meeting ON BasicInfo(meeting_id)           -- 会議IDによる検索用
CREATE INDEX idx_basicinfo_company ON BasicInfo(client_company_name)  -- 顧客企業名による検索用
CREATE INDEX idx_basicinfo_industry ON BasicInfo(industry_type)       -- 業種による検索用

CREATE INDEX idx_comments_segment ON Comments(segment_id)              -- セグメントIDによる検索用
CREATE INDEX idx_comments_meeting ON Comments(meeting_id)              -- 会議IDによる検索用
CREATE INDEX idx_comments_user ON Comments(user_id)                    -- ユーザーIDによる検索用
CREATE INDEX idx_comments_datetime ON Comments(inserted_datetime)      -- 投稿日時による検索用

CREATE INDEX idx_comment_reads_datetime ON CommentReads(read_datetime) -- 既読日時による検索用

---トリガーログ
    CREATE TABLE [dbo].[TriggerLog](
        [log_id] [int] IDENTITY(1,1) PRIMARY KEY,
        [event_type] [varchar](20) NOT NULL,
        [table_name] [varchar](100) NOT NULL,
        [record_id] [int] NOT NULL,
        [event_time] [datetime] NOT NULL,
        [additional_info] [nvarchar](MAX) NULL
    );



