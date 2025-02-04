CREATE TABLE MeetingMemo (
    -- 主キーと外部キー
    meeting_memo_id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    
    -- 基本情報
    title NVARCHAR(200) NOT NULL,                -- メモのタイトル
    [description] NVARCHAR(MAX),                   -- メモの内容
    meeting_datetime DATETIME NOT NULL,          -- 会議実施日時
    
    -- 監査情報
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,
    
    -- 外部キー制約
    CONSTRAINT FK_MeetingMemo_Users 
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- インデックス
CREATE INDEX idx_meeting_memo_user ON MeetingMemo(user_id);
CREATE INDEX idx_meeting_memo_datetime ON MeetingMemo(meeting_datetime);

