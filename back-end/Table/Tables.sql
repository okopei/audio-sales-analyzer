-- ユーザー管理
CREATE TABLE Users (
    user_id INT PRIMARY KEY IDENTITY(1,1),           -- ユーザーの一意識別子
    email NVARCHAR(256) NOT NULL UNIQUE,             -- メールアドレス
    password_hash NVARCHAR(MAX) NOT NULL,            -- パスワードハッシュ
    display_name NVARCHAR(100) NOT NULL,             -- 表示名
    role_type NVARCHAR(50) NOT NULL,                 -- ロール（admin, manager, user）
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL
)

-- 会議情報
CREATE TABLE Meetings (
    meeting_id INT PRIMARY KEY IDENTITY(1,1),        -- 会議の一意識別子
    user_id INT NOT NULL,                            -- 作成者のユーザーID
    title NVARCHAR(200) NOT NULL,                    -- 会議タイトル
    meeting_datetime DATETIME NOT NULL,              -- 会議実施日時
    duration_seconds INT,                            -- 会議時間（秒）
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT FK_Meetings_Users
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
)

-- 会議の音声データ
CREATE TABLE MeetingAudio (
    audio_id INT PRIMARY KEY IDENTITY(1,1),          -- 音声データの一意識別子
    meeting_id INT NOT NULL,                         -- 関連する会議ID
    file_name NVARCHAR(200) NOT NULL,                -- 音声ファイル名
    file_path NVARCHAR(1000) NOT NULL,               -- 音声ファイルパス
    file_size BIGINT NOT NULL,                       -- ファイルサイズ（バイト）
    duration_seconds INT,                            -- 音声時間（秒）
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT FK_MeetingAudio_Meetings
        FOREIGN KEY (meeting_id) REFERENCES Meetings(meeting_id)
)

-- 文字起こし処理状態
CREATE TABLE MeetingTranscript (
    transcript_id INT PRIMARY KEY IDENTITY(1,1),     -- 文字起こし処理の一意識別子
    meeting_id INT NOT NULL,                         -- 関連する会議ID
    audio_id INT NOT NULL,                           -- 関連する音声ID
    status NVARCHAR(50) NOT NULL,                    -- 処理状態（waiting, processing, completed, error）
    error_message NVARCHAR(MAX),                     -- エラーメッセージ（エラー時のみ）
    start_datetime DATETIME,                         -- 処理開始日時
    end_datetime DATETIME,                           -- 処理完了日時
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT FK_MeetingTranscript_Meetings
        FOREIGN KEY (meeting_id) REFERENCES Meetings(meeting_id),
    CONSTRAINT FK_MeetingTranscript_Audio
        FOREIGN KEY (audio_id) REFERENCES MeetingAudio(audio_id)
)


-- 話者マスタ
CREATE TABLE Speakers (
    speaker_id INT PRIMARY KEY IDENTITY(1,1),         -- 話者の一意識別子
    speaker_name NVARCHAR(50) NOT NULL,               -- 話者名
    speaker_role NVARCHAR(100),                       -- 話者の役割（例：営業、顧客など）
    user_id INT NULL,                                 -- ユーザーと紐付く場合のみ設定
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT FK_Speakers_Users
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
)

-- 会話の参加者情報
CREATE TABLE Participants (
    meeting_id INT NOT NULL,                          -- 関連する会議ID
    speaker_id INT NOT NULL,                          -- 話者ID（Speakersテーブルから）
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT PK_Participants PRIMARY KEY (meeting_id, speaker_id),
    CONSTRAINT FK_Participants_Meetings
        FOREIGN KEY (meeting_id) REFERENCES Meetings(meeting_id),
    CONSTRAINT FK_Participants_Speakers
        FOREIGN KEY (speaker_id) REFERENCES Speakers(speaker_id)
)

-- ミーティングメモ（文字起こし結果を含む）
CREATE TABLE MeetingMemo (
    memo_id INT PRIMARY KEY IDENTITY(1,1),           -- メモの一意識別子
    user_id INT NOT NULL,                            -- メモの作成者
    speaker_id INT NOT NULL,                         -- 発言者
    meeting_id INT NOT NULL,                         -- 関連する会議ID
    title NVARCHAR(200) NOT NULL,                    -- メモのタイトル
    content NVARCHAR(MAX),                           -- メモの内容
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT FK_MeetingMemo_Users 
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT FK_MeetingMemo_Speakers
        FOREIGN KEY (speaker_id) REFERENCES Speakers(speaker_id),
    CONSTRAINT FK_MeetingMemo_Meetings
        FOREIGN KEY (meeting_id) REFERENCES Meetings(meeting_id)
)

-- メッセージ（チャット表示用）
CREATE TABLE Messages (
    message_id INT PRIMARY KEY IDENTITY(1,1),         -- メッセージの一意識別子
    meeting_id INT NOT NULL,                          -- 関連する会議ID
    memo_id INT NOT NULL,                            -- 関連するメモID
    speaker_id INT NOT NULL,                         -- 発話者ID
    display_order INT NOT NULL,                       -- 表示順序
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    CONSTRAINT FK_Messages_Meetings
        FOREIGN KEY (meeting_id) REFERENCES Meetings(meeting_id),
    CONSTRAINT FK_Messages_MeetingMemo
        FOREIGN KEY (memo_id) REFERENCES MeetingMemo(memo_id),
    CONSTRAINT FK_Messages_Participants
        FOREIGN KEY (meeting_id, speaker_id) REFERENCES Participants(meeting_id, speaker_id)
)

-- 既読状態管理
CREATE TABLE MessageReads (
    message_id INT NOT NULL,                         -- 既読されたメッセージID
    reader_id INT NOT NULL,                          -- 既読したユーザーID
    read_datetime DATETIME NOT NULL DEFAULT GETDATE(), -- 既読した日時
    
    CONSTRAINT PK_MessageReads PRIMARY KEY (message_id, reader_id),
    CONSTRAINT FK_MessageReads_Messages
        FOREIGN KEY (message_id) REFERENCES Messages(message_id),
    CONSTRAINT FK_MessageReads_Users
        FOREIGN KEY (reader_id) REFERENCES Users(user_id)
)

-- インデックス
CREATE INDEX idx_users_email ON Users(email)                            -- メールアドレスによる検索用
CREATE INDEX idx_users_role ON Users(role_type)                         -- ロールによる検索用

CREATE INDEX idx_meetings_user ON Meetings(user_id)                     -- ユーザーIDによる検索用
CREATE INDEX idx_meetings_datetime ON Meetings(meeting_datetime)        -- 会議日時による検索用

CREATE INDEX idx_meeting_audio_meeting ON MeetingAudio(meeting_id)      -- 会議IDによる検索用

CREATE INDEX idx_meeting_transcript_meeting ON MeetingTranscript(meeting_id) -- 会議IDによる検索用
CREATE INDEX idx_meeting_transcript_audio ON MeetingTranscript(audio_id)    -- 音声IDによる検索用
CREATE INDEX idx_meeting_transcript_status ON MeetingTranscript(status)     -- 状態による検索用

CREATE INDEX idx_speakers_user ON Speakers(user_id)                      -- ユーザーIDによる検索用
CREATE INDEX idx_speakers_name ON Speakers(speaker_name)                 -- 話者名による検索用

CREATE INDEX idx_participants_speaker ON Participants(speaker_id)         -- 話者IDによる検索用

CREATE INDEX idx_meeting_memo_user ON MeetingMemo(user_id)               -- ユーザーIDによる検索用
CREATE INDEX idx_meeting_memo_speaker ON MeetingMemo(speaker_id)         -- 話者IDによる検索用
CREATE INDEX idx_meeting_memo_meeting ON MeetingMemo(meeting_id)         -- 会議IDによる検索用
CREATE INDEX idx_meeting_memo_datetime ON MeetingMemo(inserted_datetime) -- 日時による検索用

CREATE INDEX idx_messages_meeting ON Messages(meeting_id)                -- 会議IDによる検索用
CREATE INDEX idx_messages_memo ON Messages(memo_id)                      -- メモIDによる検索用
CREATE INDEX idx_messages_speaker ON Messages(speaker_id)                -- 話者IDによる検索用
CREATE INDEX idx_messages_display_order ON Messages(display_order)        -- 表示順による検索用

CREATE INDEX idx_message_reads_datetime ON MessageReads(read_datetime)    -- 既読日時による検索用